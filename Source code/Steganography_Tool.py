import os
import cv2
import numpy as np
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QMessageBox, QTabWidget, QGroupBox, QTextEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon


def sanitize_filename(filename):
    """Sanitize filename to avoid invalid characters."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", filename)


def extract_multiple_files(stego_file, output_dir):
    """Extract multiple hidden files from a stego image."""
    img = cv2.imread(stego_file)
    if img is None:
        raise ValueError("❌ Failed to read stego image. Ensure it's the correct modified image.")

    flat_img = img.flatten()
    offset = 0

    print(f"🔍 Loaded stego image: {stego_file}")
    print(f"🟢 First 100 bytes of image data: {flat_img[:100]}")  # Debugging

    while offset < len(flat_img):
        if offset + 4 > len(flat_img):
            print("⚠️ No more embedded data found.")
            break

        file_size = int.from_bytes(flat_img[offset:offset + 4].tobytes(), byteorder="big")
        offset += 4

        file_name = ""
        while offset < len(flat_img):
            byte = flat_img[offset]
            offset += 1
            if byte == 0:
                break
            file_name += chr(byte)

        file_name = sanitize_filename(file_name)
        if not file_name:
            print("⚠️ Skipping file with empty or invalid name.")
            offset += file_size
            continue

        if offset + file_size > len(flat_img):
            print(f"❌ Error: File size ({file_size} bytes) exceeds image data size at offset {offset}.")
            break

        file_data = flat_img[offset:offset + file_size].tobytes()
        offset += file_size

        output_file = os.path.join(output_dir, file_name)
        with open(output_file, "wb") as f:
            f.write(file_data)

        print(f"✅ Extracted {file_name} to {output_file}")


def hide_multiple_files(cover_file, embed_files, output_file):
    """Hide multiple files inside an image."""
    img = cv2.imread(cover_file)
    if img is None:
        raise ValueError("❌ Failed to read cover image.")

    flat_img = img.flatten()
    total_size = 0

    combined_data = bytearray()
    for embed_file in embed_files:
        with open(embed_file, "rb") as f:
            file_data = f.read()
        file_name = os.path.basename(embed_file).encode("utf-8")
        file_size = len(file_data).to_bytes(4, byteorder="big")
        combined_data += file_size + file_name + b'\x00' + file_data
        total_size += 4 + len(file_name) + 1 + len(file_data)

    print(f"📥 Embedding {len(embed_files)} files. Total data size: {total_size} bytes")

    if total_size > len(flat_img):
        raise ValueError("❌ Files too large to hide in image.")

    # Embed data at the beginning of the image
    flat_img[:total_size] = np.frombuffer(combined_data, dtype=np.uint8)

    # Debugging: Check if data is correctly modified
    print(f"🟢 First 100 bytes of modified image data: {flat_img[:100]}")

    img = flat_img.reshape(img.shape)
    success = cv2.imwrite(output_file, img)
    if not success:
        raise ValueError("❌ Failed to save stego image. Check output path and format.")

    print(f"✅ Successfully hid data in {output_file}")
#Drag and drop 
class DragDropLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.setText(urls[0].toLocalFile())

class StegoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Steganography Tool")
        self.setWindowIcon(QIcon("icon.ico"))
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet(self.get_stylesheet())  # Apply custom stylesheet

        # Main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # Tab widget for Encrypt and Decrypt
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Encrypt Tab
        self.encrypt_tab = QWidget()
        self.encrypt_layout = QVBoxLayout(self.encrypt_tab)
        self.tabs.addTab(self.encrypt_tab, "Encrypt")
        self.tabs.setStyleSheet("QTabBar::tab { height: 30px; width: 150px; }")

        # Cover Image Group
        self.cover_group = QGroupBox("Cover Image 🖼️")
        self.cover_group.setStyleSheet("QGroupBox { font-size: 22px; }")
        self.cover_layout = QVBoxLayout(self.cover_group)
        self.cover_file_input = QLineEdit()
        self.cover_file_input = DragDropLineEdit()
        self.cover_file_input.setPlaceholderText("Select a cover image")
        self.cover_file_button = QPushButton("Browse")
        self.cover_file_button.setFixedSize(90, 40)
        self.cover_file_button.setStyleSheet("QPushButton { font-size: 18px;}")
        #self.cover_file_button.setStyleSheet("QGroupBox { font-size: 22px; }")
        self.cover_file_button.setIcon(QIcon.fromTheme("folder"))
        self.cover_file_button.clicked.connect(self.browse_cover_file)
        self.cover_layout.addWidget(self.cover_file_input)
        self.cover_layout.addWidget(self.cover_file_button)
        self.encrypt_layout.addWidget(self.cover_group)

        # Files to Hide Group
        self.embed_group = QGroupBox("Files to Hide 🪪")
        self.embed_group.setStyleSheet("QGroupBox { font-size: 22px; }")
        self.embed_layout = QVBoxLayout(self.embed_group)
        self.embed_files_input = QLineEdit()
        self.embed_files_input = DragDropLineEdit()
        self.embed_files_input.setPlaceholderText("Select file to hide")
        self.embed_files_button = QPushButton("Browse")
        self.embed_files_button.setFixedSize(90, 40)
        self.embed_files_button.setStyleSheet("QPushButton { font-size: 18px;}")
        self.embed_files_button.setIcon(QIcon.fromTheme("document-open"))
        self.embed_files_button.clicked.connect(self.browse_embed_files)
        self.embed_layout.addWidget(self.embed_files_input)
        self.embed_layout.addWidget(self.embed_files_button)
        self.encrypt_layout.addWidget(self.embed_group)

        # Output Image Group
        self.output_group = QGroupBox("Output Image 🔏")
        self.output_group.setStyleSheet("QGroupBox { font-size: 22px; }") 
        self.output_layout = QVBoxLayout(self.output_group)
        self.output_file_input = QLineEdit()
        self.output_file_input = DragDropLineEdit()
        self.output_file_input.setPlaceholderText("Save the output image")
        self.output_file_button = QPushButton("Browse")
        self.output_file_button.setFixedSize(90, 40)
        self.output_file_button.setStyleSheet("QPushButton { font-size: 18px;}")
        self.output_file_button.setIcon(QIcon.fromTheme("document-save"))
        self.output_file_button.clicked.connect(self.browse_output_file)
        self.output_layout.addWidget(self.output_file_input)
        self.output_layout.addWidget(self.output_file_button)
        self.encrypt_layout.addWidget(self.output_group)

        # Encrypt Button
        self.encrypt_button = QPushButton("Encrypt")
        self.encrypt_button.setIcon(QIcon.fromTheme("document-encrypt"))
        self.encrypt_button.setFixedSize(200, 50)  # Set button size
        self.encrypt_button.clicked.connect(self.encode)
        self.encrypt_layout.addWidget(self.encrypt_button)
        self.encrypt_button.setStyleSheet("QPushButton { font-size: 18px;}")


        # Decrypt Tab
        self.decrypt_tab = QWidget()
        self.decrypt_layout = QVBoxLayout(self.decrypt_tab)
        self.tabs.addTab(self.decrypt_tab, "Decrypt")

        # Stego Image Group
        self.stego_group = QGroupBox("Stego Image")
        self.stego_group.setStyleSheet("QGroupBox { font-size: 22px; border-radius: 10px;}")
        self.stego_layout = QVBoxLayout(self.stego_group)
        self.stego_file_input = QLineEdit()
        self.stego_file_input = DragDropLineEdit()
        self.stego_file_input.setPlaceholderText("Select a stego image")
        self.stego_file_button = QPushButton("Browse")
        self.stego_file_button.setFixedSize(90, 40)
        self.stego_file_button.setStyleSheet("QPushButton { font-size: 18px;}")
        self.stego_file_button.setIcon(QIcon.fromTheme("folder"))
        self.stego_file_button.clicked.connect(self.browse_stego_file)
        self.stego_layout.addWidget(self.stego_file_input)
        self.stego_layout.addWidget(self.stego_file_button)
        self.decrypt_layout.addWidget(self.stego_group)

        # Output Directory Group
        self.output_dir_group = QGroupBox("Output Directory")
        self.output_dir_group.setStyleSheet("QGroupBox { font-size: 22px;}")
        self.output_dir_layout = QVBoxLayout(self.output_dir_group)
        self.output_dir_input = QLineEdit()
        self.output_dir_input = DragDropLineEdit()
        self.output_dir_input.setPlaceholderText("Select an output directory")
        self.output_dir_button = QPushButton("Browse")
        self.output_dir_button.setFixedSize(90, 40)
        self.output_dir_button.setStyleSheet("QPushButton { font-size: 18px; border-radius: 5px;}")
        self.output_dir_button.setIcon(QIcon.fromTheme("folder"))
        self.output_dir_button.clicked.connect(self.browse_output_dir)
        self.output_dir_layout.addWidget(self.output_dir_input)
        self.output_dir_layout.addWidget(self.output_dir_button)
        self.decrypt_layout.addWidget(self.output_dir_group)

        # Decrypt Button
        self.decrypt_button = QPushButton("Decrypt")
        self.decrypt_button.setFixedSize(200, 50)
        self.decrypt_button.setIcon(QIcon.fromTheme("document-decrypt"))
        self.decrypt_button.clicked.connect(self.decode)
        self.decrypt_layout.addWidget(self.decrypt_button)
        self.decrypt_button.setStyleSheet("QPushButton { font-size: 18px;}")

    def get_stylesheet(self):
        """Return a custom stylesheet for the application with a Minimalist Monochrome theme."""
        return """
        QMainWindow {
            background-color: #000000;
        }
        QGroupBox {
            background-color: #222222;
            color: #FFFFFF;
            border: 2px solid #444444;
            border-radius: 10px;
            margin-top: 10px;
            padding-top: 15px;
            font-size: 16px;
        }
        QLineEdit {
            background-color: #333333;
            color: #FFFFFF;
            border: 1px solid #555555;
            border-radius: 5px;
            padding: 5px;
            font-size: 14px;
        }
        QPushButton {
            background-color: #555555;
            color: #FFFFFF;
            border: none;
            border-radius: 5px;
            padding: 10px;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: #777777;
        }
        QPushButton:pressed {
            background-color: #AAAAAA;
        }
        QTabWidget::pane {
            border: 1px solid #444444;
            border-radius: 5px;
            background-color: #222222;
        }
        QTabBar::tab {
            background-color: #333333;
            color: #FFFFFF;
            padding: 10px;
            border: 1px solid #444444;
            border-radius: 5px;
            font-size: 16px;
        }
        QTabBar::tab:selected {
            background-color: #555555;
            color: #FFFFFF;
        }
        """


    def browse_cover_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Cover Image", "", "Images (*.png *.jpg *.bmp)")
        if filename:
            self.cover_file_input.setText(filename)

    def browse_embed_files(self):
        filenames, _ = QFileDialog.getOpenFileNames(self, "Select Files to Hide", "", "All Files (*)")
        if filenames:
            self.embed_files_input.setText(",".join(filenames))

    def browse_output_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Output Image", "", "Images (*.png *.jpg *.bmp)")
        if filename:
            self.output_file_input.setText(filename)

    def browse_stego_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Stego Image", "", "Images (*.png *.jpg *.bmp)")
        if filename:
            self.stego_file_input.setText(filename)

    def browse_output_dir(self):
        dirname = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dirname:
            self.output_dir_input.setText(dirname)

    def encode(self):
        try:
            cover_file = self.cover_file_input.text()
            embed_files = self.embed_files_input.text().split(",")
            output_file = self.output_file_input.text()
            hide_multiple_files(cover_file, embed_files, output_file)
            QMessageBox.information(self, "Success", "Files successfully hidden in the image.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def decode(self):
        try:
            stego_file = self.stego_file_input.text()
            output_dir = self.output_dir_input.text()
            extract_multiple_files(stego_file, output_dir)
            QMessageBox.information(self, "Success", "Files successfully extracted.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


if __name__ == "__main__":
    app = QApplication([])
    window = StegoApp()
    window.show()
    app.exec_()