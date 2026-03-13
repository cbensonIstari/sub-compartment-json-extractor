"""Allow running as: python3 -m src.web"""
from .app import app

print("\n  JSON Sub-Compartment Extractor")
print("  Open http://localhost:5001 in your browser\n")
app.run(debug=True, port=5001)
