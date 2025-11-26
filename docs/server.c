#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#include <wordexp.h>

#define MAX_BUFFER_SIZE 4096
#define MAX_EVENTS 64

void send_msg(int sock, const char *msg);
void handle_get_command(int sock, const char *args);
void handle_run_command(int sock, const char *args);
void handle_exit_command(int sock, const char *args);
void handle_power_command(int sock, const char *args);

static volatile int current_fd = -1;

typedef struct {
    const char *name;
    void (*handler)(int, const char *);
} command_t;

command_t commands[] = {{"get", handle_get_command},
                        {"run", handle_run_command},
                        {"exit", handle_exit_command},
                        {"power", handle_power_command},
                        {NULL, NULL}};

typedef struct {
    int fd;
    char buffer[MAX_BUFFER_SIZE];
    size_t buffer_len;
} client_conn_t;

static int make_socket_non_blocking(int sfd) {
    int flags = fcntl(sfd, F_GETFL, 0);
    if (flags == -1) {
        perror("fcntl(F_GETFL)");
        return -1;
    }
    flags |= O_NONBLOCK;
    if (fcntl(sfd, F_SETFL, flags) == -1) {
        perror("fcntl(F_SETFL)");
        return -1;
    }
    return 0;
}

void send_msg(int sock, const char *msg) {
    uint32_t len = strlen(msg);
    uint32_t net_len = htonl(len);
    if (send(sock, &net_len, sizeof(net_len), 0) != sizeof(net_len)) {
        perror("send length");
    }
    if (send(sock, msg, len, 0) != len) {
        perror("send message");
    }
}

void stream_directory(int sock, const char *abs_path, const char *client_path) {
    char msg[PATH_MAX + 32];
    snprintf(msg, sizeof(msg), "D_START %s", client_path);
    send_msg(sock, msg);

    DIR *dir = opendir(abs_path);
    if (dir == NULL) {
        snprintf(msg, sizeof(msg), "ERROR Could not open directory %s", client_path);
        send_msg(sock, msg);
        snprintf(msg, sizeof(msg), "D_END %s", client_path);
        send_msg(sock, msg);
        return;
    }

    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }

        char entry_abs_path[PATH_MAX];
        snprintf(entry_abs_path, sizeof(entry_abs_path), "%s/%s", abs_path, entry->d_name);

        char entry_client_path[PATH_MAX];
        snprintf(entry_client_path, sizeof(entry_client_path), "%s/%s", client_path, entry->d_name);

        struct stat entry_stat;
        if (stat(entry_abs_path, &entry_stat) != 0) {
            snprintf(msg, sizeof(msg), "ERROR Could not stat %s", entry_client_path);
            send_msg(sock, msg);
            continue;
        }

        if (S_ISDIR(entry_stat.st_mode)) {
            stream_directory(sock, entry_abs_path, entry_client_path);
        } else if (S_ISREG(entry_stat.st_mode)) {
            snprintf(
                msg, sizeof(msg), "FILE %s %lld", entry_client_path, (long long)entry_stat.st_size);
            send_msg(sock, msg);

            FILE *fp = fopen(entry_abs_path, "rb");
            if (fp == NULL) {
                perror("fopen after stat failed");
                // 无法在这里发送错误信息，因为客户端期望接收的是原始字节流。
                continue;
            }

            char buffer[MAX_BUFFER_SIZE];
            size_t bytes_read;
            while ((bytes_read = fread(buffer, 1, sizeof(buffer), fp)) > 0) {
                if (send(sock, buffer, bytes_read, 0) != bytes_read) {
                    perror("send file content");
                    break;
                }
            }
            fclose(fp);
        }
    }
    closedir(dir);

    snprintf(msg, sizeof(msg), "D_END %s", client_path);
    send_msg(sock, msg);
}

void handle_get_command(int sock, const char *args) {
    if (args == NULL) {
        send_msg(sock, "ERROR Missing file path.");
        return;
    }

    char file_path[PATH_MAX];
    if (args[0] == '~' && args[1] == '/') {
        const char *home = getenv("HOME");
        if (home) {
            snprintf(file_path, sizeof(file_path), "%s%s", home, args + 1);
        } else {
            strncpy(file_path, args, sizeof(file_path) - 1);
            file_path[sizeof(file_path) - 1] = '\0';
        }
    } else {
        strncpy(file_path, args, sizeof(file_path) - 1);
        file_path[sizeof(file_path) - 1] = '\0';
    }

    char resolved_path[PATH_MAX];
    if (realpath(file_path, resolved_path) == NULL) {
        send_msg(sock, "ERROR Path not found or could not be resolved.");
        return;
    }

    struct stat path_stat;
    if (stat(resolved_path, &path_stat) != 0) {
        send_msg(sock, "ERROR Path not found after resolution.");
        return;
    }

    if (S_ISDIR(path_stat.st_mode)) {
        stream_directory(sock, resolved_path, args);
    } else if (S_ISREG(path_stat.st_mode)) {
        char msg[PATH_MAX + 32];
        snprintf(msg, sizeof(msg), "FILE %s %lld", args, (long long)path_stat.st_size);
        send_msg(sock, msg);

        FILE *fp = fopen(resolved_path, "rb");
        if (fp == NULL) {
            perror("fopen after stat failed");
            return;
        }

        char buffer[MAX_BUFFER_SIZE];
        size_t bytes_read;
        while ((bytes_read = fread(buffer, 1, sizeof(buffer), fp)) > 0) {
            if (send(sock, buffer, bytes_read, 0) != bytes_read) {
                perror("send file content");
                break;
            }
        }
        fclose(fp);
    } else {
        send_msg(sock, "ERROR Path is not a file or directory.");
    }
}

void handle_run_command(int sock, const char *args) {
    if (args == NULL || strlen(args) == 0) {
        send_msg(sock, "Error: no command to run");
        return;
    }

    wordexp_t p;
    int ret;

    // 使用 WRDE_NOCMD 标志来禁用命令替换
    ret = wordexp(args, &p, WRDE_NOCMD);

    if (ret != 0) {
        const char *err_msg;
        switch (ret) {
        case WRDE_BADCHAR:
            err_msg = "Error: illegal character in command";
            break;
        case WRDE_BADVAL:
            err_msg = "Error: undefined shell variable";
            break;
        case WRDE_CMDSUB:
            err_msg = "Error: command substitution is not allowed";
            break;
        case WRDE_NOSPACE:
            err_msg = "Error: memory allocation failed (wordexp)";
            break;
        case WRDE_SYNTAX:
            err_msg = "Error: syntax error in command";
            break;
        default:
            err_msg = "Error: failed to parse command";
        }
        send_msg(sock, err_msg);
        return;
    }

    // 检查 wordexp 是否返回了任何参数
    if (p.we_wordc == 0) {
        send_msg(sock, "Error: no command to run (empty after expansion)");
        wordfree(&p);
        return;
    }

    // p.we_wordv 是一个 NULL 结尾的字符串数组 (char **),
    // p.we_wordv[0] 是命令, p.we_wordv[1...] 是参数
    int pipefd[2];
    if (pipe(pipefd) == -1) {
        perror("pipe");
        send_msg(sock, "Error: failed to create pipe");
        wordfree(&p);
        return;
    }

    pid_t pid = fork();
    if (pid == -1) {
        perror("fork");
        send_msg(sock, "Error: failed to fork");
        close(pipefd[0]);
        close(pipefd[1]);
        wordfree(&p);
        return;
    }

    // 子进程执行命令并重定向输出到管道， 父进程读取管道内容并发送回客户端
    if (pid == 0) {                     // 子进程
        close(pipefd[0]);               // 关闭读取端
        dup2(pipefd[1], STDOUT_FILENO); // 重定向 stdout 到管道
        dup2(pipefd[1], STDERR_FILENO); // 重定向 stderr 到管道
        close(pipefd[1]);

        execvp(p.we_wordv[0], p.we_wordv);

        // 如果 execvp 返回，说明发生了错误
        perror("execvp");
        exit(EXIT_FAILURE);
    } else {              // 父进程
        close(pipefd[1]); // 关闭写入端

        char buffer[1024];
        char *full_response = NULL;
        size_t total_size = 0;
        ssize_t n;

        while ((n = read(pipefd[0], buffer, sizeof(buffer))) > 0) {
            char *new_full_response = realloc(full_response, total_size + n);
            if (new_full_response == NULL) {
                free(full_response);
                send_msg(sock, "Error: memory allocation failed");
                goto cleanup;
            }
            full_response = new_full_response;
            memcpy(full_response + total_size, buffer, n);
            total_size += n;
        }

        if (full_response) {
            char *final_response = realloc(full_response, total_size + 1);
            if (final_response) {
                final_response[total_size] = '\0';
                send_msg(sock, final_response);
                free(final_response);
            } else {
                send_msg(sock, "Error: memory allocation failed");
                free(full_response);
            }
        } else {
            // 如果命令没有产生任何输出 (例如 'touch a.txt')
            // read() 会返回 0 (EOF)，full_response 为 NULL
            // 仍然发送一个空消息，表示命令已执行完毕
            send_msg(sock, "");
        }

    cleanup:
        close(pipefd[0]);
        waitpid(pid, NULL, 0);
        wordfree(&p);
    }
}

void handle_exit_command(int sock, const char *args) {
    printf("Client %d requested exit. Closing connection.\n", sock);
    close(sock);
}

void handle_power_command(int sock, const char *args) {
    if (args != NULL) {
        char send_str[64];
        // snprintf(send_str, sizeof(send_str), "power command processed for: %s", args);
        // send_msg(sock, send_str);
        if (strncmp(args, "on", 2) == 0) {
            current_fd = sock;
        } else {
            current_fd = -1;
        }
    } else {
        send_msg(sock, "power command with no args");
    }
}

void process_client_message(client_conn_t *conn) {
    while (1) {
        if (conn->buffer_len < sizeof(uint32_t)) {
            break;
        }

        uint32_t net_len;
        memcpy(&net_len, conn->buffer, sizeof(uint32_t));
        uint32_t msg_len = ntohl(net_len);

        if (conn->buffer_len < sizeof(uint32_t) + msg_len) {
            break;
        }

        char *msg = malloc(msg_len + 1);
        if (!msg) {
            perror("malloc");
            break;
        }
        memcpy(msg, conn->buffer + sizeof(uint32_t), msg_len);
        msg[msg_len] = '\0';

        char *command_name = strtok(msg, " ");
        char *args = strtok(NULL, "");

        if (command_name) {
            int found = 0;
            for (int i = 0; commands[i].name != NULL; i++) {
                if (strcmp(commands[i].name, command_name) == 0) {
                    commands[i].handler(conn->fd, args);
                    found = 1;
                    break;
                }
            }
            if (!found) {
                char error_msg[100];
                snprintf(error_msg, sizeof(error_msg), "Unknown command: %s", command_name);
                send_msg(conn->fd, error_msg);
            }
        }
        free(msg);

        size_t total_len = sizeof(uint32_t) + msg_len;
        memmove(conn->buffer, conn->buffer + total_len, conn->buffer_len - total_len);
        conn->buffer_len -= total_len;
    }
}

void *server_main_loop(void *arg) {
    int listen_sock;
    int epoll_fd;
    struct sockaddr_in server_addr;

    listen_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_sock < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    int opt = 1;
    setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(65432);
    server_addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(listen_sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("bind");
        exit(EXIT_FAILURE);
    }

    if (make_socket_non_blocking(listen_sock) < 0) {
        exit(EXIT_FAILURE);
    }

    if (listen(listen_sock, SOMAXCONN) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }

    epoll_fd = epoll_create1(0);
    if (epoll_fd < 0) {
        perror("epoll_create1");
        exit(EXIT_FAILURE);
    }

    struct epoll_event event;
    event.events = EPOLLIN | EPOLLET;
    event.data.fd = listen_sock;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, listen_sock, &event) < 0) {
        perror("epoll_ctl ADD listen_sock");
        exit(EXIT_FAILURE);
    }

    struct epoll_event *events = calloc(MAX_EVENTS, sizeof(struct epoll_event));

    printf("Server listening on port 65432\n");

    while (1) {
        int n = epoll_wait(epoll_fd, events, MAX_EVENTS, -1);
        for (int i = 0; i < n; i++) {
            if ((events[i].events & EPOLLERR) || (events[i].events & EPOLLHUP)) {
                fprintf(stderr, "epoll error on fd %d\n", events[i].data.fd);
                close(events[i].data.fd);
                continue;
            }

            if (events[i].data.fd == listen_sock) {
                while (1) {
                    struct sockaddr_in client_addr;
                    socklen_t client_len = sizeof(client_addr);
                    int conn_sock =
                        accept(listen_sock, (struct sockaddr *)&client_addr, &client_len);
                    if (conn_sock < 0) {
                        if (errno == EAGAIN || errno == EWOULDBLOCK) {
                            break;
                        }
                        perror("accept");
                        break;
                    }

                    make_socket_non_blocking(conn_sock);

                    client_conn_t *conn = calloc(1, sizeof(client_conn_t));
                    conn->fd = conn_sock;

                    event.events = EPOLLIN | EPOLLET;
                    event.data.ptr = conn;
                    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, conn_sock, &event) < 0) {
                        perror("epoll_ctl ADD conn_sock");
                        free(conn);
                    } else {
                        char ip_str[INET_ADDRSTRLEN];
                        inet_ntop(AF_INET, &client_addr.sin_addr, ip_str, sizeof(ip_str));
                        printf("Accepted connection from %s:%d (fd: %d)\n",
                               ip_str,
                               ntohs(client_addr.sin_port),
                               conn_sock);
                    }
                }
            } else {
                client_conn_t *conn = (client_conn_t *)events[i].data.ptr;
                int done = 0;
                while (1) {
                    ssize_t count = read(conn->fd,
                                         conn->buffer + conn->buffer_len,
                                         sizeof(conn->buffer) - conn->buffer_len);
                    if (count == -1) {
                        if (errno != EAGAIN) {
                            perror("read");
                            done = 1;
                        }
                        break;
                    } else if (count == 0) {
                        done = 1;
                        break;
                    }
                    conn->buffer_len += count;
                }

                if (done) {
                    printf("Client %d disconnected.\n", conn->fd);
                    close(conn->fd);
                    free(conn);
                } else {
                    process_client_message(conn);
                }
            }
        }
    }

    free(events);
    close(listen_sock);
    return NULL;
}

void *timer_rand_data_send(void *arg) {
    srand((unsigned int)time(NULL));
    while (1) {
        int target_fd = current_fd;
        if (target_fd != -1) {
            int rand_data = rand() % 100;
            char msg[12] = {0};
            printf("current rand data is %d\n", rand_data);
            snprintf(msg, sizeof(msg), "%d\n", rand_data);
            send_msg(target_fd, msg);
            usleep(500 * 1000);
        }
        usleep(100 * 1000);
    }
}

int main() {
    pthread_t server_thread_id, timer_thread_id;

    if (pthread_create(&server_thread_id, NULL, server_main_loop, NULL) != 0) {
        perror("pthread_create");
        return 1;
    }
    if (pthread_create(&timer_thread_id, NULL, timer_rand_data_send, NULL) != 0) {
        perror("pthread_create");
        return 1;
    }

    printf("Server thread started with ID %ld\n", (long)server_thread_id);

    pthread_join(server_thread_id, NULL);
    pthread_join(timer_thread_id, NULL);

    return 0;
}
