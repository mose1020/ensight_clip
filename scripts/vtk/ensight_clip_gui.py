#!/usr/bin/env python3
"""
EnSight File Clipping Tool - Interactive GUI
Interactive 3D clipping with real-time preview
"""

import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5 import QtWidgets, QtCore, QtGui
import sys
from pathlib import Path
import shutil


class EnSightClipperGUI(QtWidgets.QMainWindow):
    """Interactive GUI for EnSight clipping"""

    def __init__(self):
        super().__init__()
        self.reader = None
        self.merged_data = None
        self.clipper = None
        self.clip_function = None
        self.clip_type = "plane"
        self.input_file = None

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('EnSight Clipper - Interactive 3D Tool')
        self.setGeometry(100, 100, 1400, 900)

        # Central widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QtWidgets.QHBoxLayout(central_widget)

        # Left panel - Controls
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)

        # Right panel - 3D View
        view_panel = self.create_view_panel()
        main_layout.addWidget(view_panel, 3)

        # Status bar
        self.statusBar().showMessage('Ready - Load an EnSight file to begin')

    def create_control_panel(self):
        """Create the control panel"""
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)

        # Title
        title = QtWidgets.QLabel('EnSight Clipper')
        title.setFont(QtGui.QFont('Arial', 16, QtGui.QFont.Bold))
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        # File selection
        file_group = QtWidgets.QGroupBox('Input File')
        file_layout = QtWidgets.QVBoxLayout()

        self.file_label = QtWidgets.QLabel('No file loaded')
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label)

        load_btn = QtWidgets.QPushButton('Load EnSight File')
        load_btn.clicked.connect(self.load_file)
        file_layout.addWidget(load_btn)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Clip type selection
        type_group = QtWidgets.QGroupBox('Clip Type')
        type_layout = QtWidgets.QVBoxLayout()

        self.plane_radio = QtWidgets.QRadioButton('Plane')
        self.plane_radio.setChecked(True)
        self.plane_radio.toggled.connect(lambda: self.change_clip_type('plane'))
        type_layout.addWidget(self.plane_radio)

        self.box_radio = QtWidgets.QRadioButton('Box')
        self.box_radio.toggled.connect(lambda: self.change_clip_type('box'))
        type_layout.addWidget(self.box_radio)

        self.sphere_radio = QtWidgets.QRadioButton('Sphere')
        self.sphere_radio.toggled.connect(lambda: self.change_clip_type('sphere'))
        type_layout.addWidget(self.sphere_radio)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Clip parameters
        self.param_group = QtWidgets.QGroupBox('Clip Parameters')
        self.param_layout = QtWidgets.QVBoxLayout()
        self.param_group.setLayout(self.param_layout)
        layout.addWidget(self.param_group)

        # Create plane controls by default
        self.create_plane_controls()

        # Visualization options
        vis_group = QtWidgets.QGroupBox('Visualization')
        vis_layout = QtWidgets.QVBoxLayout()

        self.show_original_cb = QtWidgets.QCheckBox('Show Original (wireframe)')
        self.show_original_cb.setChecked(True)
        self.show_original_cb.stateChanged.connect(self.update_visualization)
        vis_layout.addWidget(self.show_original_cb)

        self.show_clipped_cb = QtWidgets.QCheckBox('Show Clipped Region')
        self.show_clipped_cb.setChecked(True)
        self.show_clipped_cb.stateChanged.connect(self.update_visualization)
        vis_layout.addWidget(self.show_clipped_cb)

        # Transparency slider
        opacity_label = QtWidgets.QLabel('Clipped Opacity:')
        vis_layout.addWidget(opacity_label)

        self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(80)
        self.opacity_slider.valueChanged.connect(self.update_opacity)
        vis_layout.addWidget(self.opacity_slider)

        self.opacity_value_label = QtWidgets.QLabel('80%')
        vis_layout.addWidget(self.opacity_value_label)

        vis_group.setLayout(vis_layout)
        layout.addWidget(vis_group)

        # Variable selection
        self.var_group = QtWidgets.QGroupBox('Color by Variable')
        var_layout = QtWidgets.QVBoxLayout()

        self.var_combo = QtWidgets.QComboBox()
        self.var_combo.currentIndexChanged.connect(self.update_coloring)
        var_layout.addWidget(self.var_combo)

        self.var_group.setLayout(var_layout)
        layout.addWidget(self.var_group)

        # Action buttons
        action_group = QtWidgets.QGroupBox('Actions')
        action_layout = QtWidgets.QVBoxLayout()

        self.save_btn = QtWidgets.QPushButton('Save Clipped Data')
        self.save_btn.clicked.connect(self.save_clipped)
        self.save_btn.setEnabled(False)
        action_layout.addWidget(self.save_btn)

        reset_btn = QtWidgets.QPushButton('Reset View')
        reset_btn.clicked.connect(self.reset_camera)
        action_layout.addWidget(reset_btn)

        action_group.setLayout(action_layout)
        layout.addWidget(action_group)

        # Info panel
        info_group = QtWidgets.QGroupBox('Information')
        info_layout = QtWidgets.QVBoxLayout()

        self.info_label = QtWidgets.QLabel('No data loaded')
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()

        return panel

    def create_view_panel(self):
        """Create the 3D view panel"""
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)

        # VTK widget
        self.vtk_widget = QVTKRenderWindowInteractor(panel)
        layout.addWidget(self.vtk_widget)

        # Setup renderer
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.1, 0.1, 0.2)
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)

        # Interaction
        self.iren = self.vtk_widget.GetRenderWindow().GetInteractor()

        return panel

    def create_plane_controls(self):
        """Create controls for plane clipping"""
        # Clear existing controls
        self.clear_param_layout()

        # Origin
        origin_label = QtWidgets.QLabel('Plane Origin (X, Y, Z):')
        self.param_layout.addWidget(origin_label)

        origin_layout = QtWidgets.QHBoxLayout()
        self.plane_origin_x = QtWidgets.QDoubleSpinBox()
        self.plane_origin_x.setRange(-1000, 1000)
        self.plane_origin_x.setValue(0.0)
        self.plane_origin_x.setSingleStep(0.01)
        self.plane_origin_x.valueChanged.connect(self.update_clip)

        self.plane_origin_y = QtWidgets.QDoubleSpinBox()
        self.plane_origin_y.setRange(-1000, 1000)
        self.plane_origin_y.setValue(0.0)
        self.plane_origin_y.setSingleStep(0.01)
        self.plane_origin_y.valueChanged.connect(self.update_clip)

        self.plane_origin_z = QtWidgets.QDoubleSpinBox()
        self.plane_origin_z.setRange(-1000, 1000)
        self.plane_origin_z.setValue(0.5)
        self.plane_origin_z.setSingleStep(0.01)
        self.plane_origin_z.valueChanged.connect(self.update_clip)

        origin_layout.addWidget(self.plane_origin_x)
        origin_layout.addWidget(self.plane_origin_y)
        origin_layout.addWidget(self.plane_origin_z)
        self.param_layout.addLayout(origin_layout)

        # Normal
        normal_label = QtWidgets.QLabel('Plane Normal (X, Y, Z):')
        self.param_layout.addWidget(normal_label)

        normal_layout = QtWidgets.QHBoxLayout()
        self.plane_normal_x = QtWidgets.QDoubleSpinBox()
        self.plane_normal_x.setRange(-1, 1)
        self.plane_normal_x.setValue(0.0)
        self.plane_normal_x.setSingleStep(0.1)
        self.plane_normal_x.valueChanged.connect(self.update_clip)

        self.plane_normal_y = QtWidgets.QDoubleSpinBox()
        self.plane_normal_y.setRange(-1, 1)
        self.plane_normal_y.setValue(0.0)
        self.plane_normal_y.setSingleStep(0.1)
        self.plane_normal_y.valueChanged.connect(self.update_clip)

        self.plane_normal_z = QtWidgets.QDoubleSpinBox()
        self.plane_normal_z.setRange(-1, 1)
        self.plane_normal_z.setValue(1.0)
        self.plane_normal_z.setSingleStep(0.1)
        self.plane_normal_z.valueChanged.connect(self.update_clip)

        normal_layout.addWidget(self.plane_normal_x)
        normal_layout.addWidget(self.plane_normal_y)
        normal_layout.addWidget(self.plane_normal_z)
        self.param_layout.addLayout(normal_layout)

        # Preset normals
        preset_label = QtWidgets.QLabel('Preset Normals:')
        self.param_layout.addWidget(preset_label)

        preset_layout = QtWidgets.QHBoxLayout()

        x_btn = QtWidgets.QPushButton('X')
        x_btn.clicked.connect(lambda: self.set_plane_normal(1, 0, 0))
        preset_layout.addWidget(x_btn)

        y_btn = QtWidgets.QPushButton('Y')
        y_btn.clicked.connect(lambda: self.set_plane_normal(0, 1, 0))
        preset_layout.addWidget(y_btn)

        z_btn = QtWidgets.QPushButton('Z')
        z_btn.clicked.connect(lambda: self.set_plane_normal(0, 0, 1))
        preset_layout.addWidget(z_btn)

        self.param_layout.addLayout(preset_layout)

        # Invert
        self.plane_invert_cb = QtWidgets.QCheckBox('Invert (keep other side)')
        self.plane_invert_cb.stateChanged.connect(self.update_clip)
        self.param_layout.addWidget(self.plane_invert_cb)

    def create_box_controls(self):
        """Create controls for box clipping"""
        self.clear_param_layout()

        bounds_label = QtWidgets.QLabel('Box Bounds:')
        self.param_layout.addWidget(bounds_label)

        # X bounds
        x_layout = QtWidgets.QHBoxLayout()
        x_layout.addWidget(QtWidgets.QLabel('X:'))
        self.box_xmin = QtWidgets.QDoubleSpinBox()
        self.box_xmin.setRange(-1000, 1000)
        self.box_xmin.setValue(-0.025)
        self.box_xmin.setSingleStep(0.01)
        self.box_xmin.valueChanged.connect(self.update_clip)
        x_layout.addWidget(self.box_xmin)

        x_layout.addWidget(QtWidgets.QLabel('to'))
        self.box_xmax = QtWidgets.QDoubleSpinBox()
        self.box_xmax.setRange(-1000, 1000)
        self.box_xmax.setValue(0.025)
        self.box_xmax.setSingleStep(0.01)
        self.box_xmax.valueChanged.connect(self.update_clip)
        x_layout.addWidget(self.box_xmax)
        self.param_layout.addLayout(x_layout)

        # Y bounds
        y_layout = QtWidgets.QHBoxLayout()
        y_layout.addWidget(QtWidgets.QLabel('Y:'))
        self.box_ymin = QtWidgets.QDoubleSpinBox()
        self.box_ymin.setRange(-1000, 1000)
        self.box_ymin.setValue(-0.025)
        self.box_ymin.setSingleStep(0.01)
        self.box_ymin.valueChanged.connect(self.update_clip)
        y_layout.addWidget(self.box_ymin)

        y_layout.addWidget(QtWidgets.QLabel('to'))
        self.box_ymax = QtWidgets.QDoubleSpinBox()
        self.box_ymax.setRange(-1000, 1000)
        self.box_ymax.setValue(0.025)
        self.box_ymax.setSingleStep(0.01)
        self.box_ymax.valueChanged.connect(self.update_clip)
        y_layout.addWidget(self.box_ymax)
        self.param_layout.addLayout(y_layout)

        # Z bounds
        z_layout = QtWidgets.QHBoxLayout()
        z_layout.addWidget(QtWidgets.QLabel('Z:'))
        self.box_zmin = QtWidgets.QDoubleSpinBox()
        self.box_zmin.setRange(-1000, 1000)
        self.box_zmin.setValue(0.0)
        self.box_zmin.setSingleStep(0.01)
        self.box_zmin.valueChanged.connect(self.update_clip)
        z_layout.addWidget(self.box_zmin)

        z_layout.addWidget(QtWidgets.QLabel('to'))
        self.box_zmax = QtWidgets.QDoubleSpinBox()
        self.box_zmax.setRange(-1000, 1000)
        self.box_zmax.setValue(0.5)
        self.box_zmax.setSingleStep(0.01)
        self.box_zmax.valueChanged.connect(self.update_clip)
        z_layout.addWidget(self.box_zmax)
        self.param_layout.addLayout(z_layout)

    def create_sphere_controls(self):
        """Create controls for sphere clipping"""
        self.clear_param_layout()

        # Center
        center_label = QtWidgets.QLabel('Sphere Center (X, Y, Z):')
        self.param_layout.addWidget(center_label)

        center_layout = QtWidgets.QHBoxLayout()
        self.sphere_center_x = QtWidgets.QDoubleSpinBox()
        self.sphere_center_x.setRange(-1000, 1000)
        self.sphere_center_x.setValue(0.0)
        self.sphere_center_x.setSingleStep(0.01)
        self.sphere_center_x.valueChanged.connect(self.update_clip)

        self.sphere_center_y = QtWidgets.QDoubleSpinBox()
        self.sphere_center_y.setRange(-1000, 1000)
        self.sphere_center_y.setValue(0.0)
        self.sphere_center_y.setSingleStep(0.01)
        self.sphere_center_y.valueChanged.connect(self.update_clip)

        self.sphere_center_z = QtWidgets.QDoubleSpinBox()
        self.sphere_center_z.setRange(-1000, 1000)
        self.sphere_center_z.setValue(0.5)
        self.sphere_center_z.setSingleStep(0.01)
        self.sphere_center_z.valueChanged.connect(self.update_clip)

        center_layout.addWidget(self.sphere_center_x)
        center_layout.addWidget(self.sphere_center_y)
        center_layout.addWidget(self.sphere_center_z)
        self.param_layout.addLayout(center_layout)

        # Radius
        radius_label = QtWidgets.QLabel('Radius:')
        self.param_layout.addWidget(radius_label)

        self.sphere_radius = QtWidgets.QDoubleSpinBox()
        self.sphere_radius.setRange(0.001, 1000)
        self.sphere_radius.setValue(0.3)
        self.sphere_radius.setSingleStep(0.01)
        self.sphere_radius.valueChanged.connect(self.update_clip)
        self.param_layout.addWidget(self.sphere_radius)

    def clear_param_layout(self):
        """Clear all widgets from parameter layout"""
        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def clear_layout(self, layout):
        """Recursively clear a layout"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def change_clip_type(self, clip_type):
        """Change the clipping type"""
        self.clip_type = clip_type

        if clip_type == 'plane':
            self.create_plane_controls()
        elif clip_type == 'box':
            self.create_box_controls()
        elif clip_type == 'sphere':
            self.create_sphere_controls()

        self.update_clip()

    def set_plane_normal(self, x, y, z):
        """Set plane normal to preset values"""
        self.plane_normal_x.setValue(x)
        self.plane_normal_y.setValue(y)
        self.plane_normal_z.setValue(z)

    def load_file(self):
        """Load an EnSight file"""
        default_path = str(Path(__file__).parent / "input" / "Kanalströmung")
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Open EnSight File',
            default_path,
            'EnSight Files (*.encas *.case);;All Files (*)'
        )

        if filename:
            self.load_ensight_file(filename)

    def load_ensight_file(self, filename):
        """Load the EnSight file and setup visualization"""
        self.statusBar().showMessage('Loading file...')

        try:
            # Store file path
            self.input_file = Path(filename)

            # Create reader
            self.reader = vtk.vtkGenericEnSightReader()
            self.reader.SetCaseFileName(filename)
            self.reader.Update()

            output = self.reader.GetOutput()

            # Handle multiblock data - preserve volume cells
            if hasattr(output, 'GetNumberOfBlocks') and output.GetNumberOfBlocks() > 0:
                # Append all blocks together to preserve volume data
                append = vtk.vtkAppendFilter()

                for block_idx in range(output.GetNumberOfBlocks()):
                    block = output.GetBlock(block_idx)
                    if block and block.GetNumberOfCells() > 0:
                        append.AddInputData(block)

                append.Update()
                self.merged_data = append.GetOutput()
            else:
                self.merged_data = output

            # Get bounds and info
            bounds = self.merged_data.GetBounds()
            n_points = self.merged_data.GetNumberOfPoints()
            n_cells = self.merged_data.GetNumberOfCells()

            # Update info
            info_text = f"Points: {n_points}\n"
            info_text += f"Cells: {n_cells}\n"
            info_text += f"Bounds:\n"
            info_text += f"  X: [{bounds[0]:.3f}, {bounds[1]:.3f}]\n"
            info_text += f"  Y: [{bounds[2]:.3f}, {bounds[3]:.3f}]\n"
            info_text += f"  Z: [{bounds[4]:.3f}, {bounds[5]:.3f}]"
            self.info_label.setText(info_text)

            # Update file label
            self.file_label.setText(f"Loaded: {Path(filename).name}")

            # Populate variable combo box
            self.var_combo.clear()
            self.var_combo.addItem("None (solid color)")
            point_data = self.merged_data.GetPointData()
            for i in range(point_data.GetNumberOfArrays()):
                array_name = point_data.GetArrayName(i)
                self.var_combo.addItem(array_name)

            # Setup visualization
            self.setup_visualization()

            # Enable save button
            self.save_btn.setEnabled(True)

            self.statusBar().showMessage(f'Loaded: {Path(filename).name}')

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to load file:\n{str(e)}')
            self.statusBar().showMessage('Failed to load file')

    def setup_visualization(self):
        """Setup the 3D visualization"""
        # Clear renderer
        self.renderer.RemoveAllViewProps()

        # Original data (wireframe)
        self.original_mapper = vtk.vtkDataSetMapper()
        self.original_mapper.SetInputData(self.merged_data)
        self.original_mapper.ScalarVisibilityOff()

        self.original_actor = vtk.vtkActor()
        self.original_actor.SetMapper(self.original_mapper)
        self.original_actor.GetProperty().SetRepresentationToWireframe()
        self.original_actor.GetProperty().SetColor(0.5, 0.5, 0.5)
        self.original_actor.GetProperty().SetLineWidth(1)
        self.renderer.AddActor(self.original_actor)

        # Setup clipping
        self.update_clip()

        # Reset camera
        self.reset_camera()

        # Render
        self.vtk_widget.GetRenderWindow().Render()

    def update_clip(self):
        """Update the clipping visualization"""
        if self.merged_data is None:
            return

        # Remove old actors if they exist
        if hasattr(self, 'clipped_actor'):
            self.renderer.RemoveActor(self.clipped_actor)
        if hasattr(self, 'clip_outline_actor'):
            self.renderer.RemoveActor(self.clip_outline_actor)

        # Create appropriate clip function
        if self.clip_type == 'plane':
            origin = [
                self.plane_origin_x.value(),
                self.plane_origin_y.value(),
                self.plane_origin_z.value()
            ]
            normal = [
                self.plane_normal_x.value(),
                self.plane_normal_y.value(),
                self.plane_normal_z.value()
            ]
            invert = self.plane_invert_cb.isChecked()

            self.clip_function = vtk.vtkPlane()
            self.clip_function.SetOrigin(origin)
            self.clip_function.SetNormal(normal)

            self.clipper = vtk.vtkClipDataSet()
            self.clipper.SetInputData(self.merged_data)
            self.clipper.SetClipFunction(self.clip_function)
            self.clipper.SetInsideOut(invert)

        elif self.clip_type == 'box':
            bounds = [
                self.box_xmin.value(), self.box_xmax.value(),
                self.box_ymin.value(), self.box_ymax.value(),
                self.box_zmin.value(), self.box_zmax.value()
            ]

            self.clip_function = vtk.vtkBox()
            self.clip_function.SetBounds(bounds)

            self.clipper = vtk.vtkClipDataSet()
            self.clipper.SetInputData(self.merged_data)
            self.clipper.SetClipFunction(self.clip_function)
            self.clipper.SetInsideOut(True)  # True = keep INSIDE the box

        elif self.clip_type == 'sphere':
            center = [
                self.sphere_center_x.value(),
                self.sphere_center_y.value(),
                self.sphere_center_z.value()
            ]
            radius = self.sphere_radius.value()

            self.clip_function = vtk.vtkSphere()
            self.clip_function.SetCenter(center)
            self.clip_function.SetRadius(radius)

            self.clipper = vtk.vtkClipDataSet()
            self.clipper.SetInputData(self.merged_data)
            self.clipper.SetClipFunction(self.clip_function)
            self.clipper.SetInsideOut(True)  # True = keep INSIDE the sphere

        self.clipper.Update()

        # Get clipped output and check if it has any data
        clipped_output = self.clipper.GetOutput()
        n_clipped_points = clipped_output.GetNumberOfPoints()
        n_clipped_cells = clipped_output.GetNumberOfCells()

        print(f"DEBUG: Clipped data - Points: {n_clipped_points}, Cells: {n_clipped_cells}")

        # Extract surface geometry from clipped data for visualization
        geometry_filter = vtk.vtkGeometryFilter()
        geometry_filter.SetInputConnection(self.clipper.GetOutputPort())
        geometry_filter.Update()

        # Create mapper and actor for clipped data
        self.clipped_mapper = vtk.vtkPolyDataMapper()
        self.clipped_mapper.SetInputConnection(geometry_filter.GetOutputPort())

        # Apply coloring if selected
        self.update_coloring()

        self.clipped_actor = vtk.vtkActor()
        self.clipped_actor.SetMapper(self.clipped_mapper)
        self.clipped_actor.GetProperty().SetColor(0.8, 0.3, 0.3)
        self.clipped_actor.GetProperty().SetOpacity(0.8)
        self.clipped_actor.GetProperty().EdgeVisibilityOn()
        self.clipped_actor.GetProperty().SetEdgeColor(0.9, 0.1, 0.1)
        self.renderer.AddActor(self.clipped_actor)

        # Update info label with clipped data stats
        if hasattr(self, 'info_label'):
            current_info = self.info_label.text()
            clipped_info = f"\n\nClipped Region:\nPoints: {n_clipped_points}\nCells: {n_clipped_cells}"
            # Remove old clipped info if exists
            if "Clipped Region:" in current_info:
                current_info = current_info.split("\n\nClipped Region:")[0]
            self.info_label.setText(current_info + clipped_info)

        # Add visual guide for clip region
        self.add_clip_guide()

        # Update visibility
        self.update_visualization()

        # Render
        self.vtk_widget.GetRenderWindow().Render()

    def add_clip_guide(self):
        """Add visual guide showing the clip region"""
        if self.clip_type == 'box':
            # Create outline box to show clip bounds
            bounds = [
                self.box_xmin.value(), self.box_xmax.value(),
                self.box_ymin.value(), self.box_ymax.value(),
                self.box_zmin.value(), self.box_zmax.value()
            ]

            outline_source = vtk.vtkOutlineSource()
            outline_source.SetBounds(bounds)

            outline_mapper = vtk.vtkPolyDataMapper()
            outline_mapper.SetInputConnection(outline_source.GetOutputPort())

            self.clip_outline_actor = vtk.vtkActor()
            self.clip_outline_actor.SetMapper(outline_mapper)
            self.clip_outline_actor.GetProperty().SetColor(1.0, 0.5, 0.0)  # Orange
            self.clip_outline_actor.GetProperty().SetLineWidth(3)
            self.renderer.AddActor(self.clip_outline_actor)

        elif self.clip_type == 'sphere':
            # Create sphere wireframe to show clip bounds
            center = [
                self.sphere_center_x.value(),
                self.sphere_center_y.value(),
                self.sphere_center_z.value()
            ]
            radius = self.sphere_radius.value()

            sphere_source = vtk.vtkSphereSource()
            sphere_source.SetCenter(center)
            sphere_source.SetRadius(radius)
            sphere_source.SetThetaResolution(20)
            sphere_source.SetPhiResolution(20)

            sphere_mapper = vtk.vtkPolyDataMapper()
            sphere_mapper.SetInputConnection(sphere_source.GetOutputPort())

            self.clip_outline_actor = vtk.vtkActor()
            self.clip_outline_actor.SetMapper(sphere_mapper)
            self.clip_outline_actor.GetProperty().SetColor(1.0, 0.5, 0.0)  # Orange
            self.clip_outline_actor.GetProperty().SetRepresentationToWireframe()
            self.clip_outline_actor.GetProperty().SetLineWidth(2)
            self.clip_outline_actor.GetProperty().SetOpacity(0.5)
            self.renderer.AddActor(self.clip_outline_actor)

        elif self.clip_type == 'plane':
            # Create plane outline to show clip plane
            origin = [
                self.plane_origin_x.value(),
                self.plane_origin_y.value(),
                self.plane_origin_z.value()
            ]
            normal = [
                self.plane_normal_x.value(),
                self.plane_normal_y.value(),
                self.plane_normal_z.value()
            ]

            # Get bounds of original data to size the plane representation
            bounds = self.merged_data.GetBounds()
            max_dim = max(bounds[1]-bounds[0], bounds[3]-bounds[2], bounds[5]-bounds[4])

            plane_source = vtk.vtkPlaneSource()
            plane_source.SetCenter(origin)
            plane_source.SetNormal(normal)
            plane_source.SetOrigin(
                origin[0] - max_dim * 0.7,
                origin[1] - max_dim * 0.7,
                origin[2]
            )
            plane_source.SetPoint1(
                origin[0] + max_dim * 0.7,
                origin[1] - max_dim * 0.7,
                origin[2]
            )
            plane_source.SetPoint2(
                origin[0] - max_dim * 0.7,
                origin[1] + max_dim * 0.7,
                origin[2]
            )

            plane_mapper = vtk.vtkPolyDataMapper()
            plane_mapper.SetInputConnection(plane_source.GetOutputPort())

            self.clip_outline_actor = vtk.vtkActor()
            self.clip_outline_actor.SetMapper(plane_mapper)
            self.clip_outline_actor.GetProperty().SetColor(1.0, 0.5, 0.0)  # Orange
            self.clip_outline_actor.GetProperty().SetOpacity(0.3)
            self.renderer.AddActor(self.clip_outline_actor)

    def update_coloring(self):
        """Update the coloring based on selected variable"""
        if not hasattr(self, 'clipped_mapper'):
            return

        var_name = self.var_combo.currentText()

        if var_name == "None (solid color)":
            self.clipped_mapper.ScalarVisibilityOff()
            if hasattr(self, 'clipped_actor'):
                self.clipped_actor.GetProperty().SetColor(0.8, 0.3, 0.3)
        else:
            self.clipped_mapper.ScalarVisibilityOn()
            self.clipped_mapper.SetScalarModeToUsePointData()
            self.clipped_mapper.SelectColorArray(var_name)

            # Get data range for proper scaling
            if self.clipper:
                output = self.clipper.GetOutput()
                point_data = output.GetPointData()
                array = point_data.GetArray(var_name)
                if array:
                    data_range = array.GetRange()
                    self.clipped_mapper.SetScalarRange(data_range)

        self.vtk_widget.GetRenderWindow().Render()

    def update_visualization(self):
        """Update visibility of actors"""
        if hasattr(self, 'original_actor'):
            self.original_actor.SetVisibility(self.show_original_cb.isChecked())

        if hasattr(self, 'clipped_actor'):
            self.clipped_actor.SetVisibility(self.show_clipped_cb.isChecked())

        self.vtk_widget.GetRenderWindow().Render()

    def update_opacity(self):
        """Update opacity of clipped actor"""
        opacity = self.opacity_slider.value() / 100.0
        self.opacity_value_label.setText(f'{int(opacity * 100)}%')

        if hasattr(self, 'clipped_actor'):
            self.clipped_actor.GetProperty().SetOpacity(opacity)
            self.vtk_widget.GetRenderWindow().Render()

    def reset_camera(self):
        """Reset camera to show full dataset"""
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

    def save_clipped(self):
        """Save the clipped data"""
        if self.clipper is None:
            QtWidgets.QMessageBox.warning(self, 'Warning', 'No clipped data to save')
            return

        # Ask for output directory
        default_output = str(Path(__file__).parent / "output")
        output_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            'Select Output Directory',
            default_output
        )

        if not output_dir:
            return

        # Ask for base name
        base_name, ok = QtWidgets.QInputDialog.getText(
            self,
            'Output Name',
            'Enter base name for output files:',
            text='Kanalstroemung_clipped'
        )

        if not ok or not base_name:
            return

        try:
            self.statusBar().showMessage('Saving clipped data...')

            # Create subdirectory with base_name
            output_path = Path(output_dir) / base_name
            output_path.mkdir(parents=True, exist_ok=True)

            print(f"Creating output directory: {output_path}")

            # Get the clipped volume data (UnstructuredGrid with all cells)
            clipped_data = self.clipper.GetOutput()
            n_cells_orig = clipped_data.GetNumberOfCells()
            n_points = clipped_data.GetNumberOfPoints()

            print(f"Saving clipped data: {n_points} points, {n_cells_orig} cells")

            # Convert to tetrahedra to avoid mixed cell type issues
            # This ensures compatibility with EnSight readers
            tetra_filter = vtk.vtkDataSetTriangleFilter()
            tetra_filter.SetInputData(clipped_data)
            tetra_filter.Update()

            tetra_data = tetra_filter.GetOutput()
            n_cells = tetra_data.GetNumberOfCells()

            print(f"After tetrahedralization: {tetra_data.GetNumberOfPoints()} points, {n_cells} cells")

            # Write EnSight files - this should preserve volume data
            writer = vtk.vtkEnSightWriter()
            writer.SetInputData(tetra_data)  # Use tetrahedralized data
            writer.SetFileName(str(output_path / f"{base_name}.case"))
            writer.SetPath(str(output_path))
            writer.SetBaseName(base_name)
            writer.Write()

            # Rename .case to .encas
            temp_case = output_path / f"{base_name}.0.case"
            encas_file = output_path / f"{base_name}.encas"
            if temp_case.exists():
                temp_case.replace(encas_file)

            # Create/Copy XML metadata
            xml_dest = output_path / f"{base_name}.xml"

            if self.input_file:
                xml_source = self.input_file.parent / f"{self.input_file.stem}.xml"

                if xml_source.exists():
                    # Copy existing XML and update variable names
                    shutil.copy2(xml_source, xml_dest)
                    print(f"Copied XML metadata from source")
                else:
                    # Create new XML if source doesn't exist
                    self._create_xml_from_data(xml_dest, clipped_data)
                    print(f"Created new XML metadata")
            else:
                # No input file info, create basic XML
                self._create_xml_from_data(xml_dest, clipped_data)
                print(f"Created basic XML metadata")

            self.statusBar().showMessage(f'Saved to: {output_path}')
            QtWidgets.QMessageBox.information(
                self,
                'Success',
                f'Clipped data saved to:\n{output_path}\n\nVolume Data:\n- {n_points} points\n- {n_cells} cells\n\nFiles:\n- {base_name}.encas\n- {base_name}.xml\n- Geometry and variable files'
            )

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to save:\n{str(e)}')
            self.statusBar().showMessage('Failed to save')

    def _create_xml_from_data(self, xml_path, data):
        """Create XML metadata file from clipped data"""
        # Get all point data arrays
        point_data = data.GetPointData()

        varlist = []
        for i in range(point_data.GetNumberOfArrays()):
            array_name = point_data.GetArrayName(i)
            array = point_data.GetArray(i)
            n_components = array.GetNumberOfComponents()

            # Determine units based on variable name (common CFD variables)
            if 'pressure' in array_name.lower():
                units_label = "Pa"
                units_dims = "M/LTT"
            elif 'velocity' in array_name.lower():
                units_label = "m s^-1"
                units_dims = "L/T"
            elif 'turb_kinetic_energy' in array_name.lower():
                units_label = "m^2 s^-2"
                units_dims = "LL/TT"
            elif 'turb_diss' in array_name.lower():
                units_label = "m^2 s^-3"
                units_dims = "LL/TTT"
            elif 'temperature' in array_name.lower():
                units_label = "K"
                units_dims = "Θ"
            elif 'density' in array_name.lower():
                units_label = "kg m^-3"
                units_dims = "M/LLL"
            else:
                units_label = ""
                units_dims = ""

            varlist.append(f'      <var name ="{array_name}" ENS_UNITS_LABEL="{units_label}" ENS_UNITS_DIMS="{units_dims}"></var>')

        # Add standard variables
        varlist.append('      <var name ="Coordinates" ENS_UNITS_LABEL="m" ENS_UNITS_DIMS="L"></var>')
        varlist.append('      <var name ="Time" ENS_UNITS_LABEL="s" ENS_UNITS_DIMS="T"></var>')

        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<CEImetadata version="1.0">
  <vars>
    <metatags>
      <tag name="ENS_UNITS_LABEL" type="str"></tag>
      <tag name="ENS_UNITS_DIMS" type="str"></tag>
    </metatags>
    <varlist>
{chr(10).join(varlist)}
    </varlist>
  </vars>
  <case>
    <metatags>
        <tag name="ENS_UNITS_LABEL" type="flt">2.0</tag>
        <tag name="ENS_UNITS_DIMS" type="flt">1.0</tag>
        <tag name="ENS_UNITS_SYSTEM" type="flt">1.0</tag>
        <tag name="ENS_UNITS_SYSTEM_NAME" type="str">SI</tag>
    </metatags>
  </case>
</CEImetadata>
"""

        with open(xml_path, 'w') as f:
            f.write(xml_content)

    def closeEvent(self, event):
        """Handle window close event"""
        self.vtk_widget.close()
        event.accept()


def main():
    """Main function"""
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')

    # Auto-load default file if it exists
    default_file = Path(__file__).parent / "input" / "Kanalströmung" / "Kanalstroemung.encas"

    window = EnSightClipperGUI()

    if default_file.exists():
        window.load_ensight_file(str(default_file))

    window.show()
    window.iren.Initialize()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
