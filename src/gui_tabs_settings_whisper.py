from PySide6.QtWidgets import QLabel, QComboBox, QWidget, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt
import ctranslate2
import yaml
from voice_recorder_module import VoiceRecorder

class TranscriberSettingsTab(QWidget):
    
    def __init__(self):
        super().__init__()
        self.create_layout()

        with open('config.yaml', 'r') as f:
            config_data = yaml.safe_load(f)
            transcriber_data = config_data.get('transcriber', {})

        initial_device_value = transcriber_data.get('device', None)
        if initial_device_value is not None:
            self.device_combo.setCurrentText(str(initial_device_value))

        self.update_quantization(self.device_combo, self.quantization_combo)

        initial_quant_value = transcriber_data.get('quant', None)
        if initial_quant_value is not None:
            self.quantization_combo.setCurrentText(str(initial_quant_value))

        update_map = {
            'model': (self.model_combo, 'setCurrentText', str)
        }

        for setting, (widget, setter, caster) in update_map.items():
            initial_value = transcriber_data.get(setting, None)
            if initial_value is not None:
                getattr(widget, setter)(caster(initial_value))

    def has_cuda_device(self):
        cuda_device_count = ctranslate2.get_cuda_device_count()
        return cuda_device_count > 0

    def get_supported_quantizations(self, device_type):
        types = ctranslate2.get_supported_compute_types(device_type)
        return [q for q in types if q != 'int16']

    def update_quantization(self, device_combo, quantization_combo):
        if device_combo.currentText() == "cpu":
            quantizations = self.get_supported_quantizations("cpu")
        else:
            quantizations = self.get_supported_quantizations("cuda")
        quantization_combo.clear()
        quantization_combo.addItems(quantizations)

    def create_layout(self):
        layout = QHBoxLayout()

        # Model
        model_label = QLabel("Model")
        layout.addWidget(model_label)
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v2"])
        layout.addWidget(self.model_combo)

        # Quantization
        quantization_label = QLabel("Quant")
        layout.addWidget(quantization_label)
        self.quantization_combo = QComboBox()
        layout.addWidget(self.quantization_combo)

        # Device
        device_label = QLabel("Device")
        layout.addWidget(device_label)
        self.device_combo = QComboBox()
        device_options = ["cpu"]
        if self.has_cuda_device():
            device_options.append("cuda")
        self.device_combo.addItems(device_options)
        layout.addWidget(self.device_combo)

        self.device_combo.currentTextChanged.connect(lambda: self.update_quantization(self.device_combo, self.quantization_combo))
        self.update_quantization(self.device_combo, self.quantization_combo)

        self.setLayout(layout)
    
    def update_config(self):
        with open('config.yaml', 'r') as f:
            config_data = yaml.safe_load(f)
            transcriber_data = config_data.get('transcriber', {})

        settings_changed = False
        update_map = {
            'model': (self.model_combo, 'currentText', str),
            'quant': (self.quantization_combo, 'currentText', str),
            'device': (self.device_combo, 'currentText', str)
        }

        for setting, (widget, getter, caster) in update_map.items():
            new_value = getattr(widget, getter)()
            if new_value is not None and str(new_value) != str(transcriber_data.get(setting, '')):
                settings_changed = True
                transcriber_data[setting] = caster(new_value)
                
        if settings_changed:
            config_data['transcriber'] = transcriber_data
            with open('config.yaml', 'w') as f:
                yaml.dump(config_data, f)
        return settings_changed
