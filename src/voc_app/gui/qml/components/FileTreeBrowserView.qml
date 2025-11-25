import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt.labs.folderlistmodel
import "."
import "." as Components

Rectangle {
    id: root
    color: "#f5f5f5"

    // 允许外部传入文件根路径和控制器，默认回落到全局上下文属性
    property string basePath: (typeof fileRootPath !== "undefined" && fileRootPath) ? fileRootPath : ""
    property var fileControllerRef: typeof fileController !== "undefined" ? fileController : null
    property string selectedPath: ""
    property string filterText: ""
    property var nameFilters: filterText.length > 0 ? ["*" + filterText + "*"] : ["*"]
    // 规范化目录
    property string normalizedBasePath: basePath ? basePath.replace(/\\/g, "/") : ""
    // 用于显示的根目录名称
    property string baseDisplayName: {
        if (!normalizedBasePath)
            return "";
        const parts = normalizedBasePath.split("/");
        const candidate = parts[parts.length - 1];
        return candidate && candidate.length > 0 ? candidate : normalizedBasePath;
    }
    // 当一个文件（非目录）被选中时发出
    signal fileSelected(string filePath)
    // 允许外部传入一个自定义的预览组件
    property Component previewComponent: null
    property var previewContentItem: null
    property real scaleFactor: Components.UiTheme.controlScale

    // 这里重复定义是为了防止 fileControllerRef 为空
    function pathToUrl(path) {
        if (!fileControllerRef)
            return "";
        return fileControllerRef.pathToUrl(path) || "";
    }

    function urlToLocalPath(url) {
        if (!fileControllerRef)
            return "";
        return fileControllerRef.urlToPath(url) || "";
    }

    function relativePath(path) {
        if (!path)
            return "";
        const normalized = path.replace(/\\/g, "/");
        if (normalizedBasePath && normalized.indexOf(normalizedBasePath) === 0) {
            let rel = normalized.slice(normalizedBasePath.length);
            if (rel.startsWith("/"))
                rel = rel.slice(1);
            return rel.length > 0 ? rel : baseDisplayName;
        }
        return normalized;
    }

    // 这里是为了收起目录结构时返回原先的高度
    function clampTreeScroll() {
        if (!treePane)
            return;
        const maxY = Math.max(0, treePane.contentHeight - treePane.height);
        if (treePane.contentY > maxY)
            treePane.contentY = maxY;
    }

    function updateDefaultPreview(path) {
        if (!fileControllerRef || previewComponent || !previewContentItem)
            return;
        if ("text" in previewContentItem) {
            previewContentItem.text = fileControllerRef.readFile(path);
            return;
        }
        if (typeof previewContentItem.setText === "function")
            previewContentItem.setText(fileControllerRef.readFile(path));
    }

    SplitView {
        anchors.fill: parent

        Flickable {
            id: treePane
            implicitWidth: 380 * root.scaleFactor
            SplitView.preferredWidth: 380 * root.scaleFactor
            SplitView.fillHeight: true
            clip: true
            contentWidth: width
            contentHeight: treeColumn.height
            ScrollBar.vertical: ScrollBar {}

            Column {
                id: treeColumn
                width: treePane.width
                spacing: 2 * root.scaleFactor

                Label {
                    text: root.baseDisplayName || root.normalizedBasePath || "根目录"
                    font.bold: true
                    font.pixelSize: Components.UiTheme.fontSize("subtitle")
                    padding: 6 * root.scaleFactor
                    width: treeColumn.width
                    color: Components.UiTheme.color("textOnLight")
                }

                TextField {
                    id: filterField
                    width: treeColumn.width - 12
                    anchors.horizontalCenter: parent.horizontalCenter
                    placeholderText: "按名称过滤 (模糊匹配)"
                    font.pixelSize: Components.UiTheme.fontSize("body")
                    padding: 8 * root.scaleFactor
                    text: root.filterText
                    color: Components.UiTheme.color("textOnLight")
                    placeholderTextColor: Components.UiTheme.color("textOnLightMuted")
                    onTextChanged: root.filterText = text
                }

                Item {
                    width: treeColumn.width
                    implicitHeight: rootChildrenLoader.item ? rootChildrenLoader.item.implicitHeight : 0
                    height: implicitHeight

                    Loader {
                        id: rootChildrenLoader
                        anchors.fill: parent
                        active: root.basePath && root.basePath.length > 0
                        sourceComponent: directoryContents
                        onLoaded: {
                            const topColumn = rootChildrenLoader.item;
                            if (!topColumn)
                                return;
                            topColumn.folderPath = root.basePath;
                            topColumn.parentDepth = -1;
                        }
                    }
                }
            }

            Connections {
                target: treeColumn
                function onHeightChanged() {
                    root.clampTreeScroll();
                }
            }
        }

        Item {
            id: previewPane
            SplitView.fillWidth: true
            SplitView.fillHeight: true
            clip: true

            Loader {
                id: previewLoader
                anchors.fill: parent
                sourceComponent: root.previewComponent ? root.previewComponent : defaultPreviewComponent
                onLoaded: root.previewContentItem = previewLoader.item
            }
        }
    }

    Component {
        id: treeNodeDelegate
        Column {
            id: node
            width: treeColumn.width
            spacing: 0

            property string filePath: ""
            property string fileName: ""
            property bool fileIsDir: false
            property int depth: 0
            property bool expanded: false
            property bool hasLoadedChildren: false
            property real depthIndent: 12 * root.scaleFactor + depth * 18 * root.scaleFactor

            Item {
                width: treeColumn.width
                height: 44 * root.scaleFactor

                Row {
                    id: rowContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: node.depthIndent
                    anchors.rightMargin: 10 * root.scaleFactor
                    spacing: 6 * root.scaleFactor
                    height: implicitHeight

                    Text {
                        width: fileIsDir ? 12 : 0
                        visible: fileIsDir
                        text: expanded ? "▾" : "▸"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: Components.UiTheme.color("textOnLightMuted")
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }

                    Text {
                        id: nameLabel
                        text: depth === 0 ? root.relativePath(node.filePath) : node.fileName
                        elide: Text.ElideRight
                        color: Components.UiTheme.color("textOnLight")
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: Components.UiTheme.fontSize("body")
                    }
                }

                Rectangle {
                    z: -1
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: Math.max(Components.UiTheme.spacing("sm"), node.depthIndent - Components.UiTheme.spacing("sm"))
                    anchors.rightMargin: Components.UiTheme.spacing("sm")
                    anchors.topMargin: Components.UiTheme.spacing("xs")
                    anchors.bottomMargin: Components.UiTheme.spacing("xs")
                    radius: Components.UiTheme.radius("md")
                    color: Components.UiTheme.color("accentInfo")
                    opacity: root.selectedPath === node.filePath ? 0.25 : 0
                    border.color: root.selectedPath === node.filePath ? Components.UiTheme.color("accentInfo") : "transparent"
                    border.width: 1
                }

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    onClicked: {
                        root.selectedPath = node.filePath;
                        if (node.fileIsDir) {
                            node.expanded = !node.expanded;
                            root.clampTreeScroll();
                        } else {
                            root.updateDefaultPreview(node.filePath);
                            root.fileSelected(node.filePath);
                        }
                    }
                }
            }

            Item {
                width: treeColumn.width
                visible: node.expanded
                implicitHeight: (visible && childLoader.item && childLoader.item.implicitHeight) ? childLoader.item.implicitHeight : 0
                height: implicitHeight

                Loader {
                    id: childLoader
                    anchors.fill: parent
                    active: node.fileIsDir && (node.expanded || node.hasLoadedChildren)
                    sourceComponent: directoryContents
                    onLoaded: {
                        const childItem = childLoader.item;
                        if (!childItem)
                            return;
                        childItem.folderPath = node.filePath;
                        childItem.parentDepth = node.depth;
                        node.hasLoadedChildren = true;
                    }
                }
            }
        }
    }

    // 负责加载并显示一个指定目录下的所有内容
    Component {
        id: directoryContents
        Column {
            id: dirColumn
            width: treeColumn.width
            spacing: 0
            property string folderPath: ""
            property int parentDepth: 0

            // 模型层，QML 内置组件
            FolderListModel {
                id: folderModel
                folder: root.pathToUrl(folderPath)
                showDirsFirst: true
                showDotAndDotDot: false
                showFiles: true
                sortField: FolderListModel.Name
                sortReversed: false
                nameFilters: root.nameFilters
            }

            Repeater {
                model: folderModel
                // 为模型中的每一项创建一个委托实例
                delegate: Loader {
                    id: entryLoader
                    // 表示 model 中必须有这个属性，并自动赋值为 0...
                    required property int index
                    width: treeColumn.width
                    property int rowIndex: index
                    // 为每一项创建一个 node，用于递归
                    sourceComponent: treeNodeDelegate
                    onLoaded: {
                        const entryItem = entryLoader.item;
                        if (!entryItem)
                            return;
                        function getRole(roleName) {
                            try {
                                return folderModel.get(rowIndex, roleName);
                            } catch (e) {
                                return undefined;
                            }
                        }
                        const urlValue = getRole("fileURL") || getRole("fileUrl") || getRole("filePath");
                        let localPath = "";
                        if (urlValue !== undefined && urlValue !== null && urlValue !== "")
                            localPath = root.urlToLocalPath(urlValue);
                        if (!localPath) {
                            const fallbackPath = getRole("filePath");
                            if (fallbackPath)
                                localPath = fallbackPath;
                        }
                        let name = getRole("fileName") || getRole("fileBaseName");
                        if (!name && localPath)
                            name = localPath.split("/").pop();
                        if (!name)
                            name = dirColumn.folderPath + "/…";
                        if (!localPath)
                            localPath = dirColumn.folderPath + "/" + name;
                        const isDir = folderModel.isFolder(rowIndex);
                        entryItem.filePath = localPath;
                        entryItem.fileName = name;
                        entryItem.fileIsDir = isDir;
                        entryItem.depth = dirColumn.parentDepth + 1;
                    }
                }
            }
        }
    }

    // 默认的预览组件
    Component {
        id: defaultPreviewComponent
        ScrollView {
            clip: true

            TextArea {
                id: defaultPreviewArea
                anchors.fill: parent
                readOnly: true
                wrapMode: TextArea.Wrap
                placeholderText: "点击左侧文件即可在此预览内容"
                font.pixelSize: Components.UiTheme.fontSize("body")
            }

            // 供外部通过 previewContentItem.text 赋值
            property alias text: defaultPreviewArea.text
        }
    }
}
