# Code Scalpel Examples

This directory contains example code demonstrating Code Scalpel features.

## 📁 Directory Structure

```
examples/
├── README.md                           # This file
├── .internal/                          # Internal examples (not distributed)
│   └── (development/testing examples)
├── .deprecated/                        # Deprecated examples
│
├── # AI Agent Integration Examples
├── autogen_autonomy_example.py         # Microsoft AutoGen integration
├── crewai_autonomy_example.py          # CrewAI integration
├── crewai_refactor_demo.ipynb          # CrewAI refactoring notebook
├── langgraph_example.py                # LangGraph integration
│
├── # Core Feature Examples
├── security_analysis_example.py        # Security vulnerability scanning
├── surgical_extractor_enhanced_example.py  # Token-efficient extraction
├── sandbox_example.py                  # Speculative execution sandbox
├── error_to_diff_example.py            # Error-to-Diff autonomy engine
│
├── # Multi-Language Support
├── polyglot_extraction_demo.py         # Java/JS/TS extraction
├── polyglot_usage_guide.py             # Polyglot API guide
├── simple_polyglot_demo.py             # Quick polyglot demo
├── jsx_tsx_extraction_example.py       # React component extraction
├── HelloWorld.java                     # Sample Java file
│
├── # Advanced Features
├── graph_engine_example.py             # Cross-language dependency graphs
├── unified_sink_detector_example.py    # Advanced security detection
│
└── # Notebooks
    ├── Four_Pillars_Demo.ipynb         # Interactive feature tour
    └── crewai_refactor_demo.ipynb      # CrewAI integration demo
```

## 🚀 Getting Started

### Run Security Analysis Example
```bash
cd examples
python security_analysis_example.py
```

### Run Polyglot Extraction Demo
```bash
python polyglot_extraction_demo.py
```

### Run AI Agent Examples
```bash
# AutoGen integration
python autogen_autonomy_example.py

# CrewAI integration  
python crewai_autonomy_example.py
```

## 📚 Demo Resources

For structured demonstrations and presentations, see the [demos/](../demos/) directory which contains:
- Tier-based demo scripts
- Presentation guides
- Sample vulnerable code for security demos

## 🔧 Requirements

Most examples require only the base Code Scalpel installation:
```bash
pip install code-scalpel
```

AI agent examples require additional packages:
```bash
# For AutoGen examples
pip install pyautogen

# For CrewAI examples
pip install crewai

# For LangGraph examples
pip install langgraph langchain
```

## 📝 Notes

- Examples in `.internal/` are for development/testing and are not included in public releases
- Examples in `.deprecated/` are kept for reference but may not work with current API
- See individual example files for detailed documentation and usage instructions
