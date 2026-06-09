from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.auth.session import UserSession, user_database_path
from app.character.persona_db import CharacterPersonaDB, CharacterPersonaRecord
from app.config.character_loader import CharacterRegistry


class CharacterPersonaManagementTab(QWidget):
    """管理员：SQLite 角色人设 CRUD。"""

    def __init__(self, base_dir: Path) -> None:
        super().__init__()
        self.base_dir = base_dir
        self.db_path = user_database_path(base_dir)
        self.persona_db = CharacterPersonaDB(self.db_path)
        self._selected_record_id: int | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("角色人设管理（SQLite，管理员专用）"))
        layout.addWidget(
            QLabel(
                "人设写入 users.db 的 character_personas 表；"
                "运行时优先使用数据库内容，删除记录后会回退到角色包 card 文件。"
            )
        )

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "角色ID", "显示名", "状态", "更新时间"]
        )
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self.table)

        button_row = QHBoxLayout()
        self.refresh_button = QPushButton("刷新")
        self.save_button = QPushButton("保存修改")
        self.create_button = QPushButton("新建人设")
        self.delete_button = QPushButton("删除记录")
        self.import_button = QPushButton("从角色包导入")
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.create_button)
        button_row.addWidget(self.delete_button)
        button_row.addWidget(self.import_button)
        layout.addLayout(button_row)

        form = QFormLayout()
        self.character_id_edit = QLineEdit()
        self.display_name_edit = QLineEdit()
        self.initial_message_edit = QLineEdit()
        self.enabled_check = QCheckBox("启用人设")
        self.enabled_check.setChecked(True)
        self.persona_edit = QTextEdit()
        self.persona_edit.setPlaceholderText("在此编辑人设正文（Markdown）……")
        self.persona_edit.setMinimumHeight(180)
        form.addRow("角色 ID", self.character_id_edit)
        form.addRow("显示名称", self.display_name_edit)
        form.addRow("开场白", self.initial_message_edit)
        form.addRow("", self.enabled_check)
        form.addRow("人设内容", self.persona_edit)
        layout.addLayout(form)

        self.import_combo = QComboBox()
        self.import_combo.setPlaceholderText("选择要导入的角色包")
        layout.addWidget(QLabel("角色包导入"))
        layout.addWidget(self.import_combo)

        self.refresh_button.clicked.connect(self.load_personas)
        self.save_button.clicked.connect(self.save_selected_persona)
        self.create_button.clicked.connect(self.create_persona)
        self.delete_button.clicked.connect(self.delete_selected_persona)
        self.import_button.clicked.connect(self.import_from_package)

        self._reload_import_choices()
        self.load_personas()

    def _reload_import_choices(self) -> None:
        self.import_combo.clear()
        try:
            registry = CharacterRegistry(self.base_dir)
        except Exception:
            return
        for profile in registry.all():
            self.import_combo.addItem(
                f"{profile.display_name} ({profile.id})",
                profile.id,
            )

    def load_personas(self) -> None:
        records = self.persona_db.get_all()
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem(str(record.id)))
            self.table.setItem(row, 1, QTableWidgetItem(record.character_id))
            self.table.setItem(row, 2, QTableWidgetItem(record.display_name))
            self.table.setItem(
                row,
                3,
                QTableWidgetItem("启用" if record.is_enabled else "停用"),
            )
            self.table.setItem(row, 4, QTableWidgetItem(record.updated_at))
        self._reload_import_choices()

    def _on_row_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self._selected_record_id = None
            return
        record_id = int(self.table.item(row, 0).text())
        record = self.persona_db.get_by_id(record_id)
        if record is None:
            return
        self._fill_form(record)

    def _fill_form(self, record: CharacterPersonaRecord) -> None:
        self._selected_record_id = record.id
        self.character_id_edit.setText(record.character_id)
        self.character_id_edit.setReadOnly(True)
        self.display_name_edit.setText(record.display_name)
        self.initial_message_edit.setText(record.initial_message)
        self.enabled_check.setChecked(record.is_enabled)
        self.persona_edit.setPlainText(record.persona_text)

    def _clear_create_form(self) -> None:
        self._selected_record_id = None
        self.table.clearSelection()
        self.character_id_edit.clear()
        self.character_id_edit.setReadOnly(False)
        self.display_name_edit.clear()
        self.initial_message_edit.clear()
        self.enabled_check.setChecked(True)
        self.persona_edit.clear()

    def create_persona(self) -> None:
        self._clear_create_form()
        character_id, ok = QInputDialog.getText(
            self,
            "新建人设",
            "角色 ID（英文/数字，唯一；可与角色包 id 对应）",
        )
        if not ok or not character_id.strip():
            return
        self.character_id_edit.setText(character_id.strip())
        self.character_id_edit.setReadOnly(False)

    def save_selected_persona(self) -> None:
        character_id = self.character_id_edit.text().strip()
        display_name = self.display_name_edit.text().strip()
        persona_text = self.persona_edit.toPlainText()
        initial_message = self.initial_message_edit.text().strip()
        if not character_id or not display_name:
            QMessageBox.warning(self, "错误", "角色 ID 与显示名称不能为空。")
            return
        try:
            self.persona_db.upsert(
                character_id,
                display_name,
                persona_text,
                initial_message=initial_message,
                is_enabled=self.enabled_check.isChecked(),
                updated_by_user_id=UserSession.user_id,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        self.load_personas()
        QMessageBox.information(self, "成功", "人设已保存到 SQLite。")

    def delete_selected_persona(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一条人设记录。")
            return
        record_id = int(self.table.item(row, 0).text())
        character_id = self.table.item(row, 1).text()
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定删除角色 {character_id} 的 SQLite 人设记录吗？\n"
            "删除后将回退使用角色包 card 文件。",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.persona_db.delete_by_id(record_id)
        self._clear_create_form()
        self.load_personas()

    def import_from_package(self) -> None:
        character_id = self.import_combo.currentData()
        if not character_id:
            QMessageBox.warning(self, "提示", "请先选择要导入的角色包。")
            return
        try:
            profile = CharacterRegistry(self.base_dir).get(str(character_id))
            self.persona_db.import_from_profile(profile)
        except Exception as exc:
            QMessageBox.warning(self, "导入失败", str(exc))
            return
        self.load_personas()
        QMessageBox.information(self, "成功", "已从角色包 card 导入/覆盖到 SQLite。")
