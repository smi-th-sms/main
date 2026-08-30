# coding: utf-8
"""
Mesh Overrider Tool
A Maya tool to connect mesh display override attributes to a controller's custom attribute.
"""

import sys
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QListWidget, QAbstractItemView, QLabel,
    QWidget, QGroupBox, QMenu
)
from shiboken6 import wrapInstance
import maya.OpenMayaUI as omui
import maya.cmds as cmds


def maya_main_window():
    """Return the Maya main window widget as a Python object"""
    main_window_ptr = omui.MQtUtil.mainWindow()
    if sys.version_info.major >= 3:
        return wrapInstance(int(main_window_ptr), QWidget)
    else:
        return wrapInstance(long(main_window_ptr), QWidget)


class ContextMenu(QMenu):
    """Base context menu class"""
    
    def __init__(self, *args, **kwargs):
        super(ContextMenu, self).__init__(*args, **kwargs)
    
    def load(self):
        """Show the context menu at cursor position"""
        pos = QCursor.pos()
        point = QPoint(pos.x() - 10, pos.y() - 10)
        self.exec(point)


class ControllerContextMenu(ContextMenu):
    """Context menu for controller list"""
    
    def __init__(self, parent_widget, *args, **kwargs):
        super(ControllerContextMenu, self).__init__(*args, **kwargs)
        self.parent_widget = parent_widget
        
        self.action_add = self.addAction("Add Controller", self.add_controller)
        self.action_remove = self.addAction("Remove Controller", self.remove_controller)
        self.addSeparator()
        self.action_clear = self.addAction("Clear", self.clear_list)
    
    def add_controller(self):
        """Add selected curve to controller list"""
        sel = cmds.ls(sl=True)
        if sel:
            self.parent_widget.controller_list.clear()
            self.parent_widget.controller_list.addItem(sel[0])
    
    def remove_controller(self):
        """Remove selected item from list"""
        for item in self.parent_widget.controller_list.selectedItems():
            self.parent_widget.controller_list.takeItem(
                self.parent_widget.controller_list.row(item)
            )
    
    def clear_list(self):
        """Clear all items from list"""
        self.parent_widget.controller_list.clear()


class MeshContextMenu(ContextMenu):
    """Context menu for mesh list"""
    
    def __init__(self, parent_widget, *args, **kwargs):
        super(MeshContextMenu, self).__init__(*args, **kwargs)
        self.parent_widget = parent_widget
        
        self.action_add = self.addAction("Add Meshes", self.add_meshes)
        self.action_remove = self.addAction("Remove Selected", self.remove_meshes)
        self.addSeparator()
        self.action_clear = self.addAction("Clear", self.clear_list)
    
    def add_meshes(self):
        """Add selected meshes to list"""
        sel = cmds.ls(sl=True)
        if sel:
            self.parent_widget.mesh_list.addItems(sel)
    
    def remove_meshes(self):
        """Remove selected items from list"""
        for item in self.parent_widget.mesh_list.selectedItems():
            self.parent_widget.mesh_list.takeItem(
                self.parent_widget.mesh_list.row(item)
            )
    
    def clear_list(self):
        """Clear all items from list"""
        self.parent_widget.mesh_list.clear()


class MeshOverriderDialog(QDialog):
    """Main dialog for Mesh Overrider tool"""
    
    WINDOW_TITLE = "Mesh Display Overrider"
    ATTR_NAME = "Display_Mesh_Type"
    
    def __init__(self, parent=maya_main_window()):
        super(MeshOverriderDialog, self).__init__(parent)
        
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowType.WindowContextHelpButtonHint)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.create_widgets()
        self.create_layout()
        self.create_connections()
    
    def create_widgets(self):
        """Create UI widgets"""
        # Header
        self.header_label = QLabel("Mesh Display Override Tool")
        self.header_label.setStyleSheet(
            "QLabel { background-color: #2b2b2b; color: #ffffff; "
            "padding: 10px; font-size: 12pt; font-weight: bold; }"
        )
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Controller section
        self.controller_info_label = QLabel("Select one curve controller:")
        self.controller_list = QListWidget()
        self.controller_list.setMaximumHeight(60)
        self.controller_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.controller_context_menu = ControllerContextMenu(self, self)
        self.controller_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.controller_list.customContextMenuRequested.connect(self.controller_context_menu.load)
        
        self.select_controller_btn = QPushButton("Select Curve Controller")
        self.select_controller_btn.setStyleSheet("QPushButton { background-color: #666666; }")
        
        # Mesh section
        self.mesh_info_label = QLabel("Select meshes for override:")
        self.mesh_list = QListWidget()
        self.mesh_list.setMinimumHeight(150)
        self.mesh_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.mesh_context_menu = MeshContextMenu(self, self)
        self.mesh_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.mesh_list.customContextMenuRequested.connect(self.mesh_context_menu.load)
        
        self.select_mesh_btn = QPushButton("Add Selected Meshes")
        self.select_mesh_btn.setStyleSheet("QPushButton { background-color: #999999; }")
        
        # Action button
        self.create_connection_btn = QPushButton("Create Connection!")
        self.create_connection_btn.setMinimumHeight(50)
        self.create_connection_btn.setStyleSheet(
            "QPushButton { background-color: #4a90e2; font-size: 11pt; font-weight: bold; }"
        )
    
    def create_layout(self):
        """Create UI layout"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Header
        main_layout.addWidget(self.header_label)
        
        # Controller group
        controller_group = QGroupBox("Controller")
        controller_layout = QVBoxLayout()
        controller_layout.addWidget(self.controller_info_label)
        controller_layout.addWidget(self.controller_list)
        controller_layout.addWidget(self.select_controller_btn)
        controller_group.setLayout(controller_layout)
        main_layout.addWidget(controller_group)
        
        # Mesh group
        mesh_group = QGroupBox("Target Meshes")
        mesh_layout = QVBoxLayout()
        mesh_layout.addWidget(self.mesh_info_label)
        mesh_layout.addWidget(self.mesh_list)
        mesh_layout.addWidget(self.select_mesh_btn)
        mesh_group.setLayout(mesh_layout)
        main_layout.addWidget(mesh_group)
        
        # Action button
        main_layout.addWidget(self.create_connection_btn)
    
    def create_connections(self):
        """Connect signals to slots"""
        self.select_controller_btn.clicked.connect(self.on_select_controller)
        self.select_mesh_btn.clicked.connect(self.on_select_meshes)
        self.create_connection_btn.clicked.connect(self.on_create_connection)
    
    def on_select_controller(self):
        """Add selected curve to controller list"""
        sel = cmds.ls(sl=True)
        if not sel:
            cmds.warning("Please select a curve controller")
            return
        
        # Only keep the first selected item
        self.controller_list.clear()
        self.controller_list.addItem(sel[0])
    
    def on_select_meshes(self):
        """Add selected meshes to mesh list"""
        sel = cmds.ls(sl=True)
        if not sel:
            cmds.warning("Please select meshes")
            return
        
        self.mesh_list.addItems(sel)
    
    def get_controller(self):
        """Get the controller name from list"""
        if self.controller_list.count() == 0:
            return None
        return self.controller_list.item(0).text()
    
    def get_mesh_list(self):
        """Get all mesh names from list"""
        return [self.mesh_list.item(i).text() for i in range(self.mesh_list.count())]
    
    def on_create_connection(self):
        """Create the display override connection"""
        controller = self.get_controller()
        meshes = self.get_mesh_list()
        
        if not controller:
            cmds.warning("Please select a curve controller")
            return
        
        if not meshes:
            cmds.warning("Please add meshes to the list")
            return
        
        # Verify controller exists
        if not cmds.objExists(controller):
            cmds.warning(f"Controller '{controller}' does not exist")
            return
        
        # Add attribute to controller if it doesn't exist
        try:
            if not cmds.attributeQuery(self.ATTR_NAME, node=controller, exists=True):
                cmds.addAttr(
                    controller,
                    longName=self.ATTR_NAME,
                    attributeType="enum",
                    enumName="Normal=0:Template=1:Reference=2:",
                    keyable=True,
                    defaultValue=2
                )
                cmds.setAttr(f"{controller}.{self.ATTR_NAME}", keyable=False)
                cmds.setAttr(f"{controller}.{self.ATTR_NAME}", channelBox=True)
                print(f"Added attribute '{self.ATTR_NAME}' to {controller}")
        except Exception as e:
            cmds.warning(f"Failed to add attribute: {str(e)}")
            return
        
        # Connect meshes to controller attribute
        connected_count = 0
        for mesh in meshes:
            if not cmds.objExists(mesh):
                cmds.warning(f"Mesh '{mesh}' does not exist, skipping...")
                continue
            
            try:
                # Enable override
                cmds.setAttr(f"{mesh}.overrideEnabled", 1)
                
                # Connect the display type attribute
                cmds.connectAttr(
                    f"{controller}.{self.ATTR_NAME}",
                    f"{mesh}.overrideDisplayType",
                    force=True
                )
                connected_count += 1
                print(f"Connected: {mesh}")
            except Exception as e:
                cmds.warning(f"Failed to connect {mesh}: {str(e)}")
        
        if connected_count > 0:
            cmds.confirmDialog(
                title="Success",
                message=f"Successfully connected {connected_count} mesh(es) to {controller}",
                button=["OK"],
                defaultButton="OK"
            )
        else:
            cmds.warning("No meshes were connected")


# Global variable to store dialog instance
_mesh_overrider_dialog = None


def show():
    """
    Show the Mesh Overrider UI
    
    Usage:
        import MeshOverrider
        MeshOverrider.show()
        
        # If you need to reload:
        import importlib
        importlib.reload(MeshOverrider)
        MeshOverrider.show()
    """
    global _mesh_overrider_dialog
    
    try:
        _mesh_overrider_dialog.close()
        _mesh_overrider_dialog.deleteLater()
    except:
        pass
    
    _mesh_overrider_dialog = MeshOverriderDialog()
    _mesh_overrider_dialog.show()
    
    return _mesh_overrider_dialog


# Convenience alias
main = show


if __name__ == "__main__":
    show()

