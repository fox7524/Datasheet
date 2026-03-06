#wilkommen
#Welcome
#merhaba

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QFrame, QLineEdit,
    QListWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QPixmap
import os
import json
import sys

LIB_FILE = "lib.json"

class Datasheet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Datasheet finder")
        self.setMinimumSize(800, 420)

        self.settings = QSettings("fox", "direnc_app")
        self.lib_path = os.path.join(os.path.dirname(__file__), LIB_FILE)
        self._build_ui()
        self._load_library()
        # rebuild categories and list after merging library
        self._rebuild_categories()
        self._refresh_list()
        self._load_settings()

    def _build_ui(self):
        # Add components here. To attach datasheet files or images, set the
        # 'files' list to the file paths on your machine (example/example.jpg).
        # Example:
        # 'ESP32-S3': {'desc': '...', 'category': 'Microcontroller', 'files': ['example/example.jpg']}
        self.data = {
            'ESP32-S3-NxRx': {
                'desc': '8-bit AVR microcontroller, 32KB Flash',
                'category': 'Microcontroller',
                'files': []
            },
            'ESP-WROOM-32': {
                'desc': 'Wi-Fi + Bluetooth SoC, dual-core',
                'category': 'Microcontroller',
                'files': ['example/example.jpg']
            },
            'ESP8266': {
                'desc': 'Dual operational amplifier',
                'category': 'Analog',
                'files': []
            },
            'HCSR-04': {
                'desc': 'Ultrasonic distance sensor',
                'category': 'Sensor',
                'files': []
            }
        }

        main = QVBoxLayout(self)

        # Top: category selector
        top = QHBoxLayout()
        top.addWidget(QLabel('Categories:'))
        self.category = QComboBox()
        # categories will be populated after loading library
        self.category.currentTextChanged.connect(lambda _: self._filter_list(self.search.text()))
        top.addWidget(self.category)
        main.addLayout(top)

        # Middle: left column = search + list, right column = preview + desc
        mid = QHBoxLayout()

        left_col = QVBoxLayout()
        # Search sits left-up above the list
        self.search = QLineEdit()
        self.search.setPlaceholderText('Type to search components...')
        self.search.textChanged.connect(self._filter_list)
        left_col.addWidget(self.search)

        self.list = QListWidget()
        self.list.itemSelectionChanged.connect(self._on_list_selection)
        self.list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        left_col.addWidget(self.list)

        mid.addLayout(left_col, 40)

        right = QVBoxLayout()
        # Image preview (displays first image file if present)
        self.thumb = QLabel()
        self.thumb.setFixedSize(360, 280)
        self.thumb.setFrameShape(QFrame.Box)
        right.addWidget(self.thumb)

        # Description label
        self.desc = QLabel()
        self.desc.setWordWrap(True)
        right.addWidget(self.desc)

        # file list (paths) kept for reference but not emphasized
        self.fileList = QListWidget()
        self.fileList.setMaximumHeight(120)
        right.addWidget(self.fileList)

        mid.addLayout(right, 60)
        main.addLayout(mid)

        # populate list
        self._refresh_list()

    # Note: thumbnails/previews removed per request; files are referenced by path strings.

    def _on_component_changed(self, name):
        # kept for backward compatibility if needed
        self.search.setText('')
        items = self.list.findItems(name, Qt.MatchExactly)
        if items:
            self.list.setCurrentItem(items[0])

    def _refresh_list(self):
        self.list.clear()
        for name in sorted(self.data.keys(), key=lambda s: s.lower()):
            self.list.addItem(name)

    def _rebuild_categories(self):
        cats = set()
        for info in self.data.values():
            cats.add(info.get('category', 'Microcontrollers'))
        cats = sorted(cats)
        self.category.clear()
        self.category.addItem('All')
        for c in cats:
            self.category.addItem(c)


    def _filter_list(self, text):
        text = text.strip().lower()
        self.list.clear()
        # apply category filter first
        sel_cat = self.category.currentText() if self.category.count() else 'All'
        def cat_ok(info):
            if sel_cat in (None, '', 'All'):
                return True
            return info.get('category', 'Microcontrollers') == sel_cat

        # collect candidates
        candidates = []
        for name, info in self.data.items():
            if not cat_ok(info):
                continue
            candidates.append((name, info))

        if not text:
            names = sorted([n for n,_ in candidates], key=lambda s: s.lower())
        else:
            tokens = text.split()
            names = []
            for name, info in candidates:
                hay = (name + ' ' + info.get('desc','')).lower()
                if all(tok in hay for tok in tokens):
                    names.append(name)
            names.sort(key=lambda s: s.lower())
        for n in names:
            self.list.addItem(n)

    def _load_settings(self):
        comp = self.settings.value('component', '')
        if comp and comp in self.data:
            items = self.list.findItems(comp, Qt.MatchExactly)
            if items:
                self.list.setCurrentItem(items[0])

    def closeEvent(self, event):
        # save settings
        cur = self.list.currentItem()
        if cur:
            self.settings.setValue('component', cur.text())
        self._save_library()
        super().closeEvent(event)

    # Library persistence
    def _load_library(self):
        # default data already in self.data from _build_ui
        try:
            if os.path.exists(self.lib_path):
                with open(self.lib_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                # merge
                for name, info in raw.items():
                    files = info.get('files', [])
                    desc = info.get('desc', '')
                    cat = info.get('category', 'Microcontroller')
                    if name in self.data:
                        self.data[name].setdefault('files', []).extend(files)
                        if desc:
                            self.data[name]['desc'] = desc
                        if cat:
                            self.data[name]['category'] = cat
                    else:
                        # ensure files and category keys exist
                        self.data[name] = {'desc': desc, 'files': files, 'category': cat}
        except Exception:
            pass

    def _save_library(self):
        out = {}
        for name, info in self.data.items():
            out[name] = {
                'desc': info.get('desc', ''),
                'files': info.get('files', []),
                'category': info.get('category', 'Microcontroller')
            }
        try:
            with open(self.lib_path, 'w', encoding='utf-8') as f:
                json.dump(out, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # UI actions
    # Note: component creation / file import UI removed per request. To add or
    # attach files, edit the `self.data` dict above and set the 'files' list to
    # your filesystem paths (for example 'example/example.jpg').

    def _on_list_selection(self):
        cur = self.list.currentItem()
        if not cur:
            return
        name = cur.text()
        info = self.data.get(name, {})
        desc = info.get('desc', 'No description')
        self.desc.setText(f"<b>{name}</b><br>{desc}")
        # populate files
        self.fileList.clear()
        files = info.get('files', [])
        for f in files:
            self.fileList.addItem(f)

        # show first image (jpg/png/bmp) if available
        img_path = None
        for f in files:
            if not isinstance(f, str):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.jpg', '.jpeg', '.png', '.bmp'):
                if os.path.exists(f):
                    img_path = f
                    break
        if img_path:
            pix = QPixmap(img_path)
            if not pix.isNull():
                scaled = pix.scaled(self.thumb.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumb.setPixmap(scaled)
            else:
                self.thumb.setText('Image not available')
        else:
            # placeholder
            placeholder = QPixmap(self.thumb.size())
            placeholder.fill(Qt.lightGray)
            self.thumb.setPixmap(placeholder)
    # _import_file and _open_selected_file removed per user request.


def main():
    app = QApplication(sys.argv)
    win = Datasheet()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

    
