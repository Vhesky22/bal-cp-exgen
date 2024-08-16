
import sys
import os
import csv
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, QMessageBox, QListWidget, QDialogButtonBox,
                             QDialog, QLabel, QRadioButton, QButtonGroup, QHBoxLayout, QProgressBar)
import shutil


#Core Photo Extractor - File Name and folder creator
class BatchExtractor(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.files = []

    def initUI(self):
        self.setWindowTitle('Batch File Name Extractor')
        self.setGeometry(300, 300, 300, 150)

        layout = QVBoxLayout()

        import_button = QPushButton('Import Files', self)
        import_button.clicked.connect(self.import_files)
        layout.addWidget(import_button)

        extract_button = QPushButton('Extract File Names', self)
        extract_button.clicked.connect(self.extract_file_names)
        layout.addWidget(extract_button)

        self.list_widget = QListWidget(self)
        layout.addWidget(self.list_widget)

        sort_button = QPushButton('Sort by Folder', self)
        sort_button.clicked.connect(self.sort_by_folder)
        layout.addWidget(sort_button)

        # Add the progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # Hide initially
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def import_files(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "Select Image Files", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)", options=options)
        if files:
            self.files = files
            self.list_widget.clear()  # Clear any previous entries in the QListWidget
            QMessageBox.information(self, "Files Imported", f"{len(files)} files have been imported.")


    def extract_file_names(self):
        if not self.files:
            QMessageBox.warning(self, "No Files", "Please import files first.")
            return

        # Collect invalid files
        invalid_files = []
        valid_data = []

        # Validate filenames
        for file in self.files:
            filename = os.path.basename(file)
            name_parts = filename.split('_')

            if len(name_parts) >= 2:
                project_name = '_'.join(name_parts[:-1])

                # Extract depth range
                depth_range = name_parts[-1].split('-')
                if len(depth_range) >= 2:
                    try:
                        # Parse and format depth values
                        from_depth = float(depth_range[0])
                        to_depth_str = depth_range[1].split('.')[0]  # Integer part
                        if len(depth_range[1].split('.')) > 1:
                            to_depth_str += '.' + depth_range[1].split('.')[1]  # Decimal part if present
                        to_depth = float(to_depth_str)
                        length = to_depth - from_depth

                        # Format to 2 decimal places
                        from_depth_str = f"{from_depth:.2f}"
                        to_depth_str = f"{to_depth:.2f}"
                        length_str = f"{length:.2f}"

                        # Check for negative length
                        if length < 0:
                            invalid_files.append(filename)

                        valid_data.append([project_name, from_depth_str, to_depth_str, length_str])
                    except ValueError:
                        invalid_files.append(filename)
                else:
                    invalid_files.append(filename)
            else:
                invalid_files.append(filename)

        # Handle invalid files
        if invalid_files:
            self.list_widget.clear()  # Clear any previous entries
            self.list_widget.addItems(invalid_files)  # Add invalid filenames to QListWidget
            QMessageBox.warning(self, "Invalid Filename Formats", f"The following files have incorrect formats. Check the list for details.")
            return  # Halt the saving process and return to QWidget

        # Proceed to save the valid data
        save_path, _ = QFileDialog.getSaveFileName(self, "Save CSV File", "", "CSV Files (*.csv);;All Files (*)")
        if not save_path:
            return

        with open(save_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['PROJECT_NAME', 'FROM', 'TO', 'LENGTH'])
            writer.writerows(valid_data)

        QMessageBox.information(self, "Extraction Complete", f"File names have been extracted and saved to {save_path}")

    def sort_by_folder(self):
        if not self.files:
            QMessageBox.warning(self, "No Files", "Please import files first.")
            return

        # Step 3: Display radio buttons dialog for HCP or WCP selection
        radio_dialog = QDialog(self)
        radio_dialog.setWindowTitle("Select Prefix")
        layout = QVBoxLayout()

        radio_label = QLabel("Please select the prefix for sorting:", radio_dialog)
        layout.addWidget(radio_label)

        hcp_radio = QRadioButton("HCP")
        wcp_radio = QRadioButton("WCP")
        hcp_radio.setChecked(True)  # Default selection

        button_group = QButtonGroup(radio_dialog)
        button_group.addButton(hcp_radio)
        button_group.addButton(wcp_radio)

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(hcp_radio)
        radio_layout.addWidget(wcp_radio)
        layout.addLayout(radio_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)

        button_box.accepted.connect(lambda: self.set_prefix(hcp_radio.isChecked(), radio_dialog))
        button_box.rejected.connect(radio_dialog.reject)

        radio_dialog.setLayout(layout)
        radio_dialog.exec_()

        if not self.selected_prefix:
            return  # User canceled the dialog

        folder_path = QFileDialog.getExistingDirectory(self, "Select Directory to Sort Files")
        if not folder_path:
            return

        # Show confirmation dialog
        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle("Restore Source Folder")
        layout = QVBoxLayout()

        label = QLabel("Do you want to restore the images in the source folder?", confirm_dialog)
        layout.addWidget(label)

        confirm_button_box = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No, confirm_dialog)
        layout.addWidget(confirm_button_box)

        confirm_button_box.accepted.connect(lambda: self.process_files(folder_path, copy_files=True, dialog=confirm_dialog))
        confirm_button_box.rejected.connect(lambda: self.process_files(folder_path, copy_files=False, dialog=confirm_dialog))

        confirm_dialog.setLayout(layout)
        confirm_dialog.exec_()

    def set_prefix(self, is_hcp_selected, dialog):
        self.selected_prefix = "HCP" if is_hcp_selected else "WCP"
        dialog.accept()

    def process_files(self, folder_path, copy_files, dialog):
        if not self.files:
            QMessageBox.warning(self, "No Files", "No files to process.")
            dialog.accept()
            return

        hole_id_folders = {}

        total_files = len(self.files)
        self.progress_bar.setMaximum(total_files)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)  # Show the progress bar

        for i, file in enumerate(self.files):
            filename = os.path.basename(file)
            parts = filename.split('-')

            if len(parts) < 3:
                print(f"Skipping file {filename} due to incorrect format.")
                self.list_widget.addItem(f"Skipping file {filename} due to incorrect format.")
                continue

            hole_id = f"{self.selected_prefix}-{parts[1]}-{parts[2].split('_')[0]}"

            if hole_id not in hole_id_folders:
                dest_folder = os.path.join(folder_path, hole_id)
                if not os.path.exists(dest_folder):
                    os.makedirs(dest_folder)
                hole_id_folders[hole_id] = dest_folder

            dest_folder = hole_id_folders[hole_id]
            try:
                if copy_files:
                    shutil.copy(file, os.path.join(dest_folder, filename))
                else:
                    os.rename(file, os.path.join(dest_folder, filename))
            except Exception as e:
                print(f"Failed to {'copy' if copy_files else 'move'} {filename} to {dest_folder}: {e}")

            # Update progress bar
            self.progress_bar.setValue(i + 1)
            QApplication.processEvents()  # Keep the UI responsive

        self.progress_bar.setVisible(False)  # Hide the progress bar when done
        dialog.accept()
        QMessageBox.information(self, "Sorting Complete", "Files have been sorted into folders.")



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = BatchExtractor()
    ex.show()
    sys.exit(app.exec_())
