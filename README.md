# PySLM Slicer

A professional-grade SLM (Selective Laser Melting) slicer application built with Clean Architecture principles and Domain-Driven Design.

## Features

- **Clean Architecture**: Separation of concerns with domain, application, infrastructure, and presentation layers
- **Domain-Driven Design**: Core business logic isolated from framework dependencies
- **Modern GUI**: Cura-inspired user interface with Dear PyGui and PyVista 3D rendering
- **PySLM Integration**: Powered by the PySLM library for advanced laser path generation
- **Multiple File Formats**: Support for STL, 3MF, OBJ, and AMF mesh files
- **Interactive 3D Viewport**: Real-time model manipulation with gradient backgrounds and smooth shading
- **Process Parameter Control**: Comprehensive slicing parameters for laser power, scan speed, hatch spacing, and more

## Architecture

```
src/
├── domain/              # Business logic and entities
│   ├── models.py        # Core domain models (HatchPath, Layer, BuildStyle, SLMPart)
│   └── interfaces.py    # Domain interfaces
├── application/         # Use cases and application services
│   ├── scene_manager.py # 3D scene and object management
│   └── slicer_service.py # Slicing orchestration
├── infrastructure/      # External adapters and implementations
│   ├── adapters/
│   │   ├── pyslm_adapter.py  # PySLM library integration
│   │   └── opc_ua_adapter.py # OPC UA communication
│   └── repositories/
│       └── asset_loader.py   # Mesh file loading
└── presentation/        # User interface
    ├── theme.py         # Cura-inspired UI theme
    ├── main_window.py   # Main application window
    └── viewport_manager.py # 3D viewport rendering
```

## Installation

### Prerequisites

- Python 3.9+
- Git

### Setup

1. Clone the repository with submodules:
```bash
git clone --recursive https://github.com/ShahidMustafa-PhD/Slicer-PySLM.git
cd Slicer-PySLM
```

2. Create and activate virtual environment:
```bash
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install dearpygui pyvista trimesh numpy
```

## Usage

Launch the application:
```bash
python main.py
```

### Keyboard Shortcuts

- **Ctrl+O**: Open model file(s)
- **Ctrl+D**: Duplicate selected object
- **Ctrl+A**: Select all objects
- **Del**: Delete selected object
- **F**: Fit all objects in view
- **Home**: Reset camera
- **G/S/R**: Switch to Move/Scale/Rotate tool

### Workflow

1. **Import Models**: Use File → Open Model(s) or click the Import button
2. **Transform Objects**: Select objects and use transform tools (Move, Scale, Rotate)
3. **Configure Parameters**: Adjust process parameters in the right panel
   - Layer thickness
   - Laser power and scan speed
   - Hatch spacing and angle
4. **Slice**: Click "Slice Now" to generate toolpaths
5. **Export**: Save the build file for machine execution

## Process Parameters

- **Layer Thickness**: 20-50 μm (typical: 30 μm)
- **Laser Power**: Material-dependent (typical: 200W for Ti-6Al-4V)
- **Scan Speed**: 800-1200 mm/s
- **Hatch Spacing**: 0.08-0.12 mm
- **Hatch Angle Increment**: 67° (optimal for uniform properties)

## Supported Materials

- Ti-6Al-4V (Titanium alloy)
- 316L Stainless Steel
- AlSi10Mg (Aluminum alloy)
- IN718 (Nickel superalloy)

## Development

The project follows Clean Architecture principles:

- **Domain Layer**: Pure business logic, no external dependencies
- **Application Layer**: Use cases and orchestration
- **Infrastructure Layer**: Adapters for external libraries and services
- **Presentation Layer**: UI implementation using Dear PyGui

### Key Design Patterns

- **Dependency Inversion**: High-level modules independent of low-level details
- **Repository Pattern**: Abstract data access
- **Adapter Pattern**: Integrate external libraries (PySLM, PyVista)
- **Service Layer**: Encapsulate business operations

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **PySLM**: Core slicing engine ([https://github.com/drlukeparry/pyslm](https://github.com/drlukeparry/pyslm))
- **Dear PyGui**: GPU-accelerated GUI framework
- **PyVista**: 3D visualization with VTK
- **Trimesh**: Mesh processing and file I/O

## Contact

**Dr. Shahid Mustafa**  
COMSATS University Islamabad, Attock Campus  
Email: shahidmustafa@cuiatd.edu.pk

---

Built with ❤️ for the additive manufacturing community.
