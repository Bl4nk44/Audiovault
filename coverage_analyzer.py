import xml.etree.ElementTree as ET

tree = ET.parse('backend/coverage.xml')
root = tree.getroot()

files = []
for package in root.findall('.//package'):
    for cls in package.findall('.//class'):
        name = cls.get('filename')
        rate = float(cls.get('line-rate'))
        lines = len(cls.findall('.//line'))
        if lines > 20: # skip small files
            files.append((name, rate, lines))

# Sort by coverage rate (ascending)
files.sort(key=lambda x: x[1])

print("Top 15 files to improve coverage (more than 20 lines):")
for name, rate, lines in files[:15]:
    print(f"{name:50} | {rate*100:6.1f}% | {lines:4} lines")
