import RPi.GPIO as GPIO

class GPIOController:
    def __init__(self, input_pins_config, output_pins_config, PUL_Status, default_state):
        """
        初始化GPIO控制器
        :param input_pins_config: 输入引脚配置字典 {名称: BCM编号}
        :param output_pins_config: 输出引脚配置字典 {名称: BCM编号}
        """
        GPIO.setmode(GPIO.BCM)
        
        # 保存引脚配置
        self.input_pins = input_pins_config
        self.output_pins = output_pins_config
        
        # 初始化输入引脚
        for pin_name, pin_num in self.input_pins.items():
            if PUL_Status == 1:
                GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            else:
                GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # 初始化输出引脚
        for pin_name, pin_num in self.output_pins.items():
            GPIO.setup(pin_num, GPIO.OUT)
            if default_state:
                GPIO.output(pin_num, GPIO.HIGH)
            else:
                GPIO.output(pin_num, GPIO.LOW)
    
    def read_input(self, pin_name):
        """
        读取指定输入引脚状态
        :param pin_name: 输入引脚名称
        :return: GPIO.HIGH 或 GPIO.LOW
        """
        if pin_name not in self.input_pins:
            raise ValueError(f"未知输入引脚: {pin_name}")
        return GPIO.input(self.input_pins[pin_name])
    
    def read_all_inputs(self):
        """读取所有输入引脚状态"""
        return {name: not self.read_input(name) for name in self.input_pins}
    
    def set_output(self, pin_name, state):
        """
        设置单个输出引脚状态
        :param pin_num: BCM编号
        :param state: GPIO.HIGH 或 GPIO.LOW
        """
        if pin_name not in self.output_pins:
            raise ValueError(f"未知输出引脚: {pin_name}")
        GPIO.output(self.output_pins[pin_name], state)
    
    def set_all_outputs(self, state):
        """设置所有输出引脚状态"""
        for pin in self.output_pins:
            self.set_output(pin, state)
    '''    
    def toggle_output(self, pin_num):
        """翻转单个输出引脚状态"""
        current = GPIO.input(pin_num)
        self.set_output(pin_num, not current)
    
    def toggle_all_outputs(self):
        """翻转所有输出引脚状态"""
        for pin in self.output_pins:
            self.toggle_output(pin)
    '''

    def cleanup(self):
        """释放GPIO资源"""
        GPIO.cleanup()
        print("GPIO资源已释放")