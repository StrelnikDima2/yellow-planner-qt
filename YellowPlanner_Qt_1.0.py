# -*- coding: utf-8 -*-
"""YellowPlanner Qt 1.0 — отдельная версия на PySide6.
Совместима с форматом %APPDATA%/YellowPlanner/tasks.json от Tkinter-версий.
"""
import json, os, sys, uuid, time, threading, webbrowser
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QDateTime, QByteArray, QSize, QPoint, QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QColor, QIcon, QPixmap, QFont, QPainter, QDesktopServices
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame, QMenu, QMessageBox, QDialog,
    QDialogButtonBox, QFormLayout, QDateTimeEdit, QComboBox, QSlider, QCheckBox,
    QFileDialog, QColorDialog, QFontComboBox, QSpinBox, QSystemTrayIcon)

APP_NAME = "YellowPlanner Qt 1.0"
BG, PANEL, INK, MUTED = "#F5F6F8", "#FFFFFF", "#252A32", "#858B96"
ACCENT, ACCENT_DARK, BORDER = "#B58A55", "#967044", "#E8E9EC"
PALETTE = ["#FFFFFF", "#F8F1E8", "#F7EEEE", "#EDF3EE", "#EEF1F6", "#F2EEF6", "#EDF4F3", "#F1F2F3"]
BRIGHT_PALETTE = ["#FFF176", "#FFB74D", "#FF8A80", "#F48FB1", "#CE93D8", "#90CAF9", "#80DEEA", "#A5D6A7", "#DCE775", "#B0BEC5"]
EMAIL = "strelnikdima@mail.ru"


def data_dir():
    p = Path(os.environ.get("APPDATA") or Path.home()) / "YellowPlanner"
    p.mkdir(parents=True, exist_ok=True)
    return p

DATA_FILE = data_dir() / "tasks.json"


def load_data():
    try:
        d = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(d, dict): raise ValueError("Invalid data")
    except (OSError, ValueError, json.JSONDecodeError):
        d = {"tasks": [], "settings": {}}
    d.setdefault("tasks", []); d.setdefault("settings", {})
    defaults = {"startup": False, "topmost": True, "hide_done": False,
                "alarm_sound": "Мелодия", "card_scale": 1.0, "theme": "Светлая"}
    for k, v in defaults.items(): d["settings"].setdefault(k, v)
    for t in d["tasks"]:
        t.setdefault("id", str(uuid.uuid4())); t.setdefault("subs", []); t.setdefault("color", PALETTE[0])
        t.setdefault("expanded", True); t.setdefault("alarm", ""); t.setdefault("done", False)
        t.setdefault("font_family", "Segoe UI"); t.setdefault("font_size", 11)
        t.setdefault("attachment", t.get("image", ""))
        for s in t["subs"]: s.setdefault("id", str(uuid.uuid4())); s.setdefault("done", False)
    return d


def save_data(data):
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)

def set_startup(enabled):
    startup = Path(os.environ.get('APPDATA') or Path.home()) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup' / 'YellowPlannerQt.bat'
    if enabled:
        if getattr(sys, 'frozen', False):
            command = f'\"{sys.executable}\"'
        else:
            command = f'\"{sys.executable}\" \"{Path(__file__).resolve()}\"'
        startup.parent.mkdir(parents=True, exist_ok=True)
        startup.write_text('@echo off\nstart \"\" ' + command + '\n', encoding='utf-8')
    else:
        try: startup.unlink()
        except FileNotFoundError: pass


def svg_icon(path, color=INK, size=18):
    paths = {
        "file": '<path d="M6 2.8h7l5 5V21H6z"/><path d="M13 2.8V8h5M9 13h6M9 16.5h6"/>',
        "plus": '<path d="M12 5v14M5 12h14"/>',
        "check": '<path d="m5 12 4 4L19 6"/>',
        "more": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
        "chevron": '<path d="m6 9 6 6 6-6"/>',
        "settings": '<circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.2 2-2 2-2-1.2-.2-.1a7 7 0 0 1-2 .8l-.5 2.2h-2.8l-.5-2.2a7 7 0 0 1-2-.8l-.2.1-2 1.2-2-2 1.2-2 .1-.2a7 7 0 0 1-.8-2L2.8 12v-2.8L5 8.7a7 7 0 0 1 .8-2l-.1-.2-1.2-2 2-2 2 1.2.2.1a7 7 0 0 1 2-.8l.5-2.2H14l.5 2.2a7 7 0 0 1 2 .8l.2-.1 2-1.2 2 2-1.2 2-.1.2a7 7 0 0 1 .8 2l2.2.5V12l-2.2.5a7 7 0 0 1-.8 2Z"/>',
        "clip": '<path d="m8 12.5 6.8-6.8a3 3 0 0 1 4.2 4.2l-8.5 8.5a5 5 0 0 1-7.1-7.1l8.2-8.2"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
        "trash": '<path d="M4 7h16M10 11v6m4-6v6M6 7l1 14h10l1-14M9 7V4h6v3"/>',
        "edit": '<path d="m4 16.5-.8 4.3 4.3-.8L20 7.5 16.5 4zM14.8 5.7l3.5 3.5"/>',
    }
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{paths[path]}</g></svg>'
    pix = QPixmap(size, size); pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix); QSvgRenderer(QByteArray(svg.encode())).render(painter); painter.end()
    return QIcon(pix)


class TaskCard(QFrame):
    def __init__(self, app, task):
        super().__init__(); self.app = app; self.task = task; self.drag_origin = None
        self.setObjectName("taskCard")
        self.setStyleSheet(f"QFrame#taskCard{{background:{'#F0F1F3' if task.get('done') else task.get('color', PALETTE[0])};border:1px solid {BORDER};border-radius:12px;}}")
        outer = QVBoxLayout(self); density = max(.35, min(1.5, float(app.settings.get('card_scale', 1))))
        outer.setContentsMargins(round(8*density), round(5*density), round(8*density), round(5*density)); outer.setSpacing(round(4*density))
        row = QHBoxLayout(); row.setSpacing(6)
        done = task.get('done', False)
        self.done_btn = QPushButton("✓" if done else "○"); self.done_btn.setObjectName("checkButton")
        self.done_btn.setStyleSheet(f"color:{'#43866C' if not done else '#C46D6D'};font-size:19px;border:0;background:transparent")
        self.done_btn.clicked.connect(lambda: app.toggle_task(task)); row.addWidget(self.done_btn)
        title = QLabel(task.get('text','')); title.setWordWrap(True); title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        font = QFont(task.get('font_family','Segoe UI'), int(task.get('font_size',11))); font.setBold(True); font.setStrikeOut(done); title.setFont(font)
        title.setStyleSheet(f"color:{'#A1A4AA' if done else INK};background:transparent;border:0")
        title.mouseDoubleClickEvent = lambda e: app.edit_task(task)
        row.addWidget(title, 1)
        if task.get('attachment') or task.get('image'):
            b = self.tool_button('file', ACCENT_DARK, lambda: app.open_attachment(task)); b.setToolTip("Открыть прикреплённый файл"); row.addWidget(b)
        b = self.tool_button('plus', ACCENT_DARK, lambda: app.add_subtask(task)); b.setToolTip("Добавить подзадачу"); row.addWidget(b)
        if task.get('subs'):
            b = QPushButton("⌄" if task.get('expanded', True) else "›"); b.setObjectName('flatTool'); b.clicked.connect(lambda: app.expand_task(task)); row.addWidget(b)
        b = self.tool_button('more', MUTED, lambda: app.task_menu(task)); b.setToolTip("Действия"); row.addWidget(b)
        outer.addLayout(row)
        if task.get('alarm'):
            try: alarm_text = datetime.fromisoformat(task['alarm']).strftime('%d.%m.%Y  %H:%M')
            except ValueError: alarm_text = task['alarm']
            ar = QHBoxLayout(); ar.addWidget(QLabel("◷  " + alarm_text)); ar.addStretch()
            clear = QPushButton("Сбросить"); clear.setObjectName('textButton'); clear.clicked.connect(lambda: app.clear_alarm(task)); ar.addWidget(clear); outer.addLayout(ar)
        if task.get('subs') and task.get('expanded', True):
            for sub in task['subs']:
                sr = QHBoxLayout(); sb = QPushButton("✓" if sub.get('done') else "○"); sb.setObjectName('subCheck'); sb.clicked.connect(lambda checked=False, s=sub: app.toggle_sub(task,s)); sr.addWidget(sb)
                sl = QLabel(sub.get('text','')); sl.setWordWrap(True); sl.setStyleSheet(f"color:{MUTED if sub.get('done') else INK};background:transparent;border:0;")
                sf = sl.font(); sf.setStrikeOut(sub.get('done',False)); sl.setFont(sf); sr.addWidget(sl,1)
                sm = QPushButton("⋯"); sm.setObjectName('flatTool'); sm.clicked.connect(lambda checked=False, s=sub: app.sub_menu(task,s)); sr.addWidget(sm)
                outer.addLayout(sr)

    def tool_button(self, icon, color, callback):
        b = QPushButton(); b.setIcon(svg_icon(icon,color)); b.setIconSize(QSize(17,17)); b.setObjectName('flatTool'); b.clicked.connect(callback); return b

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.drag_origin = event.position().toPoint()
        super().mousePressEvent(event)
    def mouseReleaseEvent(self, event):
        if self.drag_origin is not None and (event.position().toPoint()-self.drag_origin).manhattanLength() > 20:
            self.app.reorder_task(self.task, event.globalPosition().toPoint().y())
        self.drag_origin = None; super().mouseReleaseEvent(event)


class EditDialog(QDialog):
    def __init__(self, parent, title, value=""):
        super().__init__(parent); self.setWindowTitle(title); self.setMinimumWidth(440)
        lay=QVBoxLayout(self); self.edit=QLineEdit(value); self.edit.selectAll(); lay.addWidget(self.edit)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); lay.addWidget(buttons)


class SettingsDialog(QDialog):
    def __init__(self, app):
        super().__init__(app); self.app=app; self.setWindowTitle("Общие настройки"); self.setMinimumWidth(430)
        f=QVBoxLayout(self); form=QFormLayout(); f.addLayout(form)
        self.start=QCheckBox("Запускать вместе с Windows"); self.start.setChecked(app.settings.get('startup',False)); form.addRow(self.start)
        self.top=QCheckBox("Закрепить поверх других окон"); self.top.setChecked(app.settings.get('topmost',True)); form.addRow(self.top)
        self.hide=QCheckBox("Скрывать выполненные задачи"); self.hide.setChecked(app.settings.get('hide_done',False)); form.addRow(self.hide)
        self.theme=QComboBox(); self.theme.addItems(["Светлая","Тёмная"]); self.theme.setCurrentText(app.settings.get('theme','Светлая')); form.addRow("Тема",self.theme)
        self.scale=QSlider(Qt.Orientation.Horizontal); self.scale.setRange(35,150); self.scale.setValue(int(float(app.settings.get('card_scale',1))*100)); form.addRow("Плотность карточек",self.scale)
        self.scale_label=QLabel(); form.addRow("",self.scale_label); self.scale.valueChanged.connect(self.update_scale); self.update_scale(self.scale.value())
        self.sound=QComboBox(); self.sound.addItems(["Мелодия","Мягкий","Двойной сигнал"]); self.sound.setCurrentText(app.settings.get('alarm_sound','Мелодия')); form.addRow("Звук напоминания",self.sound)
        f.addWidget(QLabel("Поддержка автора · " + EMAIL))
        mail=QPushButton("Написать предложение"); mail.clicked.connect(lambda: webbrowser.open('mailto:'+EMAIL)); f.addWidget(mail)
        f.addWidget(QLabel("Формат tasks.json сохраняется совместимым с предыдущими версиями."))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); f.addWidget(buttons)
    def update_scale(self,v): self.scale_label.setText(f"{v/100:.2f}× — {'очень компактно' if v<60 else 'компактно' if v<90 else 'стандартно' if v<115 else 'просторно'}")


class Planner(QMainWindow):
    def __init__(self):
        super().__init__(); self.data=load_data(); self.settings=self.data['settings']; self.alarm_stop=threading.Event(); self.alarm_popup=None
        self.setWindowTitle(APP_NAME); self.resize(620,800); self.setMinimumSize(390,480)
        self.build_ui(); self.apply_theme(); self.render()
        self.timer=QTimer(self); self.timer.timeout.connect(self.check_alarms); self.timer.start(1000)
        if self.settings.get('topmost',True): self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True); self.show()

    def build_ui(self):
        root=QWidget(); self.setCentralWidget(root); v=QVBoxLayout(root); v.setContentsMargins(20,18,16,12); v.setSpacing(10)
        head=QHBoxLayout(); title=QLabel("Мои задачи"); title.setObjectName('heading'); head.addWidget(title); self.count=QLabel("0"); self.count.setObjectName('count'); head.addWidget(self.count); head.addStretch()
        settings=QPushButton(); settings.setIcon(svg_icon('settings',INK,20)); settings.setObjectName('flatTool'); settings.clicked.connect(self.open_settings); head.addWidget(settings); v.addLayout(head)
        sub=QLabel("Пространство для планов, идей и важных дел"); sub.setObjectName('muted'); v.addWidget(sub)
        add=QHBoxLayout(); self.new_task=QLineEdit(); self.new_task.setPlaceholderText("Новая задача…"); self.new_task.returnPressed.connect(self.add_task); add.addWidget(self.new_task,1)
        plus=QPushButton(); plus.setIcon(svg_icon('plus','#FFFFFF',20)); plus.setObjectName('addButton'); plus.clicked.connect(self.add_task); add.addWidget(plus); v.addLayout(add)
        self.scroll=QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.cards_host=QWidget(); self.cards=QVBoxLayout(self.cards_host); self.cards.setContentsMargins(2,2,8,2); self.cards.setSpacing(7); self.cards.addStretch()
        self.scroll.setWidget(self.cards_host); v.addWidget(self.scroll,1)
        self.progress=QLabel(); self.progress.setObjectName('muted'); v.addWidget(self.progress)

    def apply_theme(self):
        dark=self.settings.get('theme')=='Тёмная'; bg='#202329' if dark else BG; panel='#2B3038' if dark else PANEL; ink='#ECEEF2' if dark else INK; muted='#A0A6B0' if dark else MUTED; border='#3B424D' if dark else BORDER
        self.setStyleSheet(f"""
        QMainWindow,QWidget{{background:{bg};color:{ink};font-family:'Segoe UI';font-size:10pt;}}
        QLabel#heading{{font-size:23pt;font-weight:700;}} QLabel#muted{{color:{muted};font-size:9pt;}}
        QLabel#count{{background:{'#493F32' if dark else '#EEE8DF'};color:{ACCENT_DARK};border-radius:10px;padding:5px 10px;font-weight:700;}}
        QLineEdit,QComboBox,QDateTimeEdit{{background:{panel};border:1px solid {border};border-radius:9px;padding:10px;color:{ink};selection-background-color:{ACCENT};}}
        QPushButton{{border:0;border-radius:8px;padding:8px 12px;}} QPushButton#addButton{{background:{ACCENT};min-width:38px;min-height:38px;}}
        QPushButton#flatTool,QPushButton#checkButton,QPushButton#subCheck{{background:transparent;padding:3px;}}
        QPushButton#textButton{{background:transparent;color:{ACCENT_DARK};}}
        QScrollArea{{background:transparent;border:0;}} QSlider::groove:horizontal{{height:5px;background:{border};border-radius:2px;}} QSlider::handle:horizontal{{background:{ACCENT};width:15px;margin:-5px 0;border-radius:7px;}}
        QMenu{{background:{panel};color:{ink};border:1px solid {border};padding:5px;}} QMenu::item{{padding:7px 22px;}} QMenu::item:selected{{background:{'#493F32' if dark else '#F4F0EA'};}}
        QCheckBox{{padding:5px;}}
        """)
        self._colors=(bg,panel,ink,muted,border)

    def save(self): save_data(self.data)
    def render(self):
        while self.cards.count()>1:
            item=self.cards.takeAt(0); w=item.widget()
            if w: w.deleteLater()
        tasks=self.data['tasks']; active=[t for t in tasks if not t.get('done')]; done=[t for t in tasks if t.get('done')]
        ordered=active+done
        if self.settings.get('hide_done'): ordered=active
        for t in ordered: self.cards.insertWidget(self.cards.count()-1,TaskCard(self,t))
        total_done=sum(bool(t.get('done')) for t in tasks); self.count.setText(str(len(tasks)-total_done)); self.progress.setText(f"Выполнено: {total_done} из {len(tasks)}")
        if not ordered:
            empty=QLabel("Пока нет задач. Добавь первую!"); empty.setAlignment(Qt.AlignmentFlag.AlignCenter); empty.setStyleSheet(f"color:{self._colors[3]};padding:28px"); self.cards.insertWidget(0,empty)

    def add_task(self):
        text=self.new_task.text().strip()
        if not text:return
        self.data['tasks'].insert(0,{"id":str(uuid.uuid4()),"text":text,"done":False,"color":PALETTE[0],"expanded":True,"subs":[],"alarm":"","font_family":"Segoe UI","font_size":11,"attachment":""})
        self.new_task.clear(); self.save(); self.render()
    def toggle_task(self,t): t['done']=not t.get('done',False); self.save(); self.render()
    def toggle_sub(self,t,s): s['done']=not s.get('done',False); self.save(); self.render()
    def ask_text(self,title,value,callback):
        d=EditDialog(self,title,value)
        if d.exec() and d.edit.text().strip(): callback(d.edit.text().strip()); self.save(); self.render()
    def edit_task(self,t): self.ask_text("Название задачи",t.get('text',''),lambda x:t.__setitem__('text',x))
    def edit_sub(self,t,s): self.ask_text("Название подзадачи",s.get('text',''),lambda x:s.__setitem__('text',x))
    def add_subtask(self,t): self.ask_text("Новая подзадача","",lambda x:t.setdefault('subs',[]).append({'id':str(uuid.uuid4()),'text':x,'done':False}))
    def confirm(self,title,text): return QMessageBox.question(self,title,text)==QMessageBox.StandardButton.Yes
    def delete_task(self,t):
        if self.confirm("Удалить задачу",f"Удалить «{t.get('text','')}» и все подзадачи?"): self.data['tasks'].remove(t); self.save(); self.render()
    def delete_sub(self,t,s):
        if self.confirm("Удалить подзадачу",f"Удалить «{s.get('text','')}»?"): t['subs'].remove(s); self.save(); self.render()
    def expand_task(self,t): t['expanded']=not t.get('expanded',True); self.save(); self.render()
    def clear_alarm(self,t): t['alarm']=''; self.save(); self.render()
    def set_alarm(self,t):
        d=QDialog(self); d.setWindowTitle("Напоминание"); l=QVBoxLayout(d); edit=QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600)); edit.setCalendarPopup(True); edit.setDisplayFormat('dd.MM.yyyy HH:mm')
        if t.get('alarm'):
            try: edit.setDateTime(QDateTime.fromString(t['alarm'],Qt.DateFormat.ISODate))
            except Exception: pass
        l.addWidget(edit); buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject); l.addWidget(buttons)
        if d.exec():
            dt=edit.dateTime().toPython()
            if dt<=datetime.now(): QMessageBox.warning(self,"Напоминание","Укажите время в будущем."); return
            t['alarm']=dt.isoformat(timespec='minutes'); self.save(); self.render()
    def check_alarms(self):
        now=datetime.now(); changed=False
        for t in self.data['tasks']:
            val=t.get('alarm','')
            if val:
                try: due=datetime.fromisoformat(val)
                except ValueError: t['alarm']=''; changed=True; continue
                if due<=now: t['alarm']=''; changed=True; self.show_alarm(t.get('text',''))
        if changed:self.save();self.render()
    def show_alarm(self,text):
        if self.alarm_popup and self.alarm_popup.isVisible():return
        d=QDialog(self); self.alarm_popup=d; d.setWindowTitle("YellowPlanner — напоминание"); d.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,True)
        l=QVBoxLayout(d); h=QLabel("Время задачи!"); h.setStyleSheet("font-size:17pt;font-weight:700"); l.addWidget(h); msg=QLabel(text);msg.setWordWrap(True);l.addWidget(msg)
        stop=QPushButton("Отключить сигнал");stop.clicked.connect(d.accept);l.addWidget(stop); d.finished.connect(lambda: self.alarm_stop.set()); self.alarm_stop.clear(); d.show()
        def sound():
            try:
                import winsound
                patterns={"Мелодия":[(660,180),(880,180),(990,240),(880,180)],"Мягкий":[(523,260),(659,300),(784,360)],"Двойной сигнал":[(880,220),(880,220),(660,320)]}
                end=time.time()+60
                while time.time()<end and not self.alarm_stop.is_set():
                    for f,ms in patterns.get(self.settings.get('alarm_sound','Мелодия'),patterns['Мелодия']):
                        if self.alarm_stop.is_set():break
                        winsound.Beep(f,ms); self.alarm_stop.wait(.12)
            except Exception:pass
        threading.Thread(target=sound,daemon=True).start(); QTimer.singleShot(60000,self.alarm_stop.set)
    def choose_color(self,t):
        c=QColorDialog.getColor(QColor(t.get('color',PALETTE[0])),self,"Цвет карточки")
        if c.isValid():t['color']=c.name();self.save();self.render()
    def attach_file(self,t):
        path,_=QFileDialog.getOpenFileName(self,"Прикрепить файл")
        if path:t['attachment']=path;t.pop('image',None);self.save();self.render()
    def open_attachment(self,t):
        path=t.get('attachment') or t.get('image','')
        if path and os.path.isfile(path):
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        elif path: QMessageBox.warning(self,"Файл не найден","Возможно, файл был перемещён.")
    def task_menu(self,t):
        m=QMenu(self)
        for label,fn in [("Настроить напоминание",lambda:self.set_alarm(t)),("Звук напоминания",self.choose_alarm_sound),("Цвет карточки",lambda:self.choose_color(t)),("Шрифт и размер",lambda:self.font_settings(t)),("Прикрепить файл",lambda:self.attach_file(t))]:m.addAction(label,fn)
        if t.get('attachment') or t.get('image'):m.addAction("Убрать файл",lambda:self.remove_attachment(t))
        m.addSeparator();m.addAction("Изменить название",lambda:self.edit_task(t));m.addAction("Копировать текст",lambda:QApplication.clipboard().setText(t.get('text','')));m.addAction("Добавить подзадачу",lambda:self.add_subtask(t))
        if t.get('alarm'):m.addAction("Удалить напоминание",lambda:self.clear_alarm(t))
        m.addAction("Удалить задачу",lambda:self.delete_task(t));m.exec(self.mapToGlobal(self.rect().center()))
    def sub_menu(self,t,s):
        m=QMenu(self);m.addAction("Изменить",lambda:self.edit_sub(t,s));m.addAction("Удалить",lambda:self.delete_sub(t,s));m.exec()
    def remove_attachment(self,t):t['attachment']='';t.pop('image',None);self.save();self.render()
    def font_settings(self,t):
        d=QDialog(self);d.setWindowTitle("Шрифт задачи");f=QFormLayout(d);family=QFontComboBox();family.setCurrentFont(QFont(t.get('font_family','Segoe UI')));size=QSpinBox();size.setRange(9,24);size.setValue(int(t.get('font_size',11)));f.addRow("Шрифт",family);f.addRow("Размер",size)
        b=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);b.accepted.connect(d.accept);b.rejected.connect(d.reject);f.addRow(b)
        if d.exec():t['font_family']=family.currentFont().family();t['font_size']=size.value();self.save();self.render()
    def choose_alarm_sound(self):
        from PySide6.QtWidgets import QInputDialog
        opts=["Мелодия","Мягкий","Двойной сигнал"];v,ok=QInputDialog.getItem(self,"Звук напоминания","Выберите звук",opts,opts.index(self.settings.get('alarm_sound','Мелодия')),False)
        if ok:self.settings['alarm_sound']=v;self.save()
    def open_settings(self):
        d=SettingsDialog(self)
        if d.exec():
            self.settings.update(startup=d.start.isChecked(),topmost=d.top.isChecked(),hide_done=d.hide.isChecked(),theme=d.theme.currentText(),card_scale=d.scale.value()/100,alarm_sound=d.sound.currentText())
            set_startup(d.start.isChecked())
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,bool(self.settings['topmost']));self.show();self.apply_theme();self.save();self.render()
    def reorder_task(self,t,global_y):
        group=[x for x in self.data['tasks'] if bool(x.get('done'))==bool(t.get('done'))]
        if t not in group:return
        # Перестановка по вертикальному положению карточек в прокручиваемом списке.
        target=None
        for i in range(self.cards.count()-1):
            w=self.cards.itemAt(i).widget()
            if isinstance(w,TaskCard) and w.task is not t:
                mid=w.mapToGlobal(QPoint(0,w.height()//2)).y()
                if global_y<mid:target=w.task;break
        old=group.index(t);group.remove(t);idx=group.index(target) if target in group else len(group)
        if idx==old:return
        group.insert(idx,t);it=iter(group);self.data['tasks']=[next(it) if bool(x.get('done'))==bool(t.get('done')) else x for x in self.data['tasks']];self.save();self.render()
    def closeEvent(self,event):
        self.alarm_stop.set();self.save();event.accept()


def main():
    app=QApplication(sys.argv); app.setApplicationName("YellowPlanner"); app.setStyle('Fusion'); app.setFont(QFont("Segoe UI",10))
    w=Planner();w.show();sys.exit(app.exec())

if __name__=='__main__': main()
