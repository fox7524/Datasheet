from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QFrame, QLineEdit,
    QListWidget, QSizePolicy, QPushButton, QScrollArea
)
from PyQt5.QtCore import Qt, QSettings, QPoint
from PyQt5.QtGui import QPixmap, QCursor
import os
import json
import sys
import subprocess

JPG_FOLDER = "jpg"
PDF_FOLDER = "sheets" 
LIB_FILE = "lib.json"

class Datasheet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Datasheet Finder Pro")
        self.setMinimumSize(1000, 600)

        self.settings = QSettings("fox & callisto", "datasheet_app")
        self.lib_path = os.path.join(os.path.dirname(__file__), LIB_FILE)
        
        self.data = {}
        self.zoom_factor = -1.0  # Flag for auto-calculating fit
        self.min_zoom = 0.1
        self.last_mouse_pos = QPoint()

        self._build_ui()
        self._load_library()
        
        if self.data:
            self._rebuild_categories()
            self._refresh_list()
        else:
            self._show_empty_state()
            
        self._load_settings()

    def _build_ui(self):
        main = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel('Category:'))
        self.category = QComboBox()
        self.category.currentTextChanged.connect(lambda _: self._filter_list(self.search.text()))
        top.addWidget(self.category)
        main.addLayout(top)

        mid = QHBoxLayout()

        # Left Column
        left_col = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search components...')
        self.search.textChanged.connect(self._filter_list)
        left_col.addWidget(self.search)

        self.list = QListWidget()
        self.list.itemSelectionChanged.connect(self._on_list_selection)
        left_col.addWidget(self.list)
        mid.addLayout(left_col, 30)

        # Right Column
        right = QVBoxLayout()
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("background-color: #121212;") 
        self.scroll_area.setWidget(self.thumb)
        
        self.thumb.setMouseTracking(True)
        self.thumb.installEventFilter(self)
        
        right.addWidget(self.scroll_area)

        self.btn_open = QPushButton("📄 Open PDF")
        self.btn_open.setFixedHeight(40)
        self.btn_open.setStyleSheet("font-weight: bold; background-color: #2c3e50; color: white;")
        self.btn_open.clicked.connect(self._open_file)
        right.addWidget(self.btn_open)

        self.desc = QLabel()
        self.desc.setWordWrap(True)
        right.addWidget(self.desc)

        right.addWidget(QLabel("<b>Versions (Scroll: Zoom | Drag: Pan | Double-Click: Fit):</b>"))
        self.fileList = QListWidget()
        self.fileList.setMaximumHeight(100)
        self.fileList.itemSelectionChanged.connect(self._reset_zoom_and_load)
        right.addWidget(self.fileList)

        mid.addLayout(right, 70)
        main.addLayout(mid)

    def eventFilter(self, source, event):
        if source is self.thumb and self.thumb.pixmap():
            # 1. Mouse Wheel Zoom
            if event.type() == event.Wheel:
                angle = event.angleDelta().y()
                factor = 1.1 if angle > 0 else 0.9
                new_zoom = self.zoom_factor * factor
                
                # Use calculated min_zoom to prevent "tiny image" syndrome
                if new_zoom >= self.min_zoom and new_zoom <= 5.0:
                    self.zoom_factor = new_zoom
                    self._update_image_display()
                return True

            # 2. Left Click Panning
            elif event.type() == event.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.last_mouse_pos = event.pos()
                    self.thumb.setCursor(Qt.ClosedHandCursor)
                return True

            elif event.type() == event.MouseMove:
                if event.buttons() == Qt.LeftButton:
                    delta = event.pos() - self.last_mouse_pos
                    h_bar = self.scroll_area.horizontalScrollBar()
                    v_bar = self.scroll_area.verticalScrollBar()
                    h_bar.setValue(h_bar.value() - delta.x())
                    v_bar.setValue(v_bar.value() - delta.y())
                return True

            elif event.type() == event.MouseButtonRelease:
                self.thumb.setCursor(Qt.ArrowCursor)
                return True
            
            # 3. Double Click to Reset to Fit
            elif event.type() == event.MouseButtonDblClick:
                self._reset_zoom_and_load()
                return True

        return super().eventFilter(source, event)

    def _reset_zoom_and_load(self):
        """Forces the display to recalculate the fit for the next image"""
        self.zoom_factor = -1.0
        self._update_image_display()

    def _update_image_display(self):
        p_item = self.list.currentItem()
        v_item = self.fileList.currentItem()
        if not p_item or not v_item: return

        info = self.data.get(p_item.text(), {})
        files = info.get('files', {})
        v_data = files.get(v_item.text(), {})
        img_path = self._resolve_file_path(v_data.get('img'))

        if img_path:
            pix = QPixmap(img_path)
            if not pix.isNull():
                # --- RESOLUTION HANDLING LOGIC ---
                # Calculate the ratio needed to fit the image to the current window width
                available_width = self.scroll_area.width() - 30
                fit_ratio = available_width / pix.width()

                # If we just loaded the image, set zoom to perfectly fit
                if self.zoom_factor <= 0:
                    self.zoom_factor = fit_ratio
                
                # Lock min zoom to the fit_ratio to avoid black spaces
                self.min_zoom = fit_ratio 

                self.scroll_area.setWidgetResizable(False)
                new_width = int(pix.width() * self.zoom_factor)
                
                # SmoothTransformation is key for mixed resolutions
                scaled = pix.scaledToWidth(new_width, Qt.SmoothTransformation)
                self.thumb.setPixmap(scaled)
                self.thumb.adjustSize()
        else:
            self.thumb.clear()
            self.thumb.setText("No Image Found")

    def _resolve_file_path(self, file_path):
        if not file_path or not isinstance(file_path, str): return None
        script_dir = os.path.dirname(__file__)
        f_name = os.path.basename(file_path).lower()
        options = [os.path.join(script_dir, PDF_FOLDER, f_name), os.path.join(script_dir, JPG_FOLDER, f_name)]
        for opt in options:
            if os.path.exists(opt): return opt
        return None

    def _load_library(self):
        if not os.path.exists(self.lib_path): return
        try:
            with open(self.lib_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception as e:
            print(f"JSON Error: {e}")
            self.data = {}

    def _on_list_selection(self):
        cur = self.list.currentItem()
        if not cur: return
        name = cur.text()
        info = self.data.get(name, {})
        self.desc.setText(f"<b>{name}</b><br>{info.get('desc', '')}")
        self.fileList.clear()
        files = info.get('files', {})
        if isinstance(files, dict):
            for v_name in files.keys():
                self.fileList.addItem(v_name)
            self.fileList.setCurrentRow(0)

    def _open_file(self):
        p_item = self.list.currentItem()
        v_item = self.fileList.currentItem()
        if not p_item or not v_item: return
        files = self.data.get(p_item.text(), {}).get('files', {})
        v_data = files.get(v_item.text(), {})
        f_path = self._resolve_file_path(v_data.get('pdf'))
        if f_path:
            if sys.platform == "win32": os.startfile(f_path)
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.Popen([opener, f_path])

    def _refresh_list(self):
        self.list.clear()
        for name in sorted(self.data.keys()): self.list.addItem(name)

    def _rebuild_categories(self):
        cats = sorted({info.get('category', 'General') for info in self.data.values()})
        self.category.clear()
        self.category.addItem('All')
        self.category.addItems(cats)

    def _filter_list(self, text):
        text = text.lower()
        self.list.clear()
        sel_cat = self.category.currentText()
        for name, info in self.data.items():
            if sel_cat != 'All' and info.get('category') != sel_cat: continue
            if text in name.lower() or text in info.get('desc', '').lower():
                self.list.addItem(name)

    def _load_settings(self):
        comp = self.settings.value('component', '')
        items = self.list.findItems(comp, Qt.MatchExactly)
        if items: self.list.setCurrentItem(items[0])

    def closeEvent(self, event):
        cur = self.list.currentItem()
        if cur: self.settings.setValue('component', cur.text())
        super().closeEvent(event)

    def _show_empty_state(self):
        self.list.addItem("Library empty.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Datasheet()
    win.show()
    sys.exit(app.exec_())
