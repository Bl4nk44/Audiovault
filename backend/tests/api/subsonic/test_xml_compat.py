import xml.etree.ElementTree as ET

from app.schemas.subsonic.base import dict_to_xml


def normalize_xml(xml_str):
    """Normalize XML string for comparison."""
    return ET.tostring(ET.fromstring(xml_str), encoding="unicode")


def test_xml_list_flattening():
    """
    Verify that a list in a dict is flattened, not wrapped in a redundant container.
    """
    data = {
        "indexes": {
            "lastModified": "123",
            "index": [
                {"name": "A", "artist": [{"id": "1", "name": "Abba"}]},
                {"name": "B", "artist": [{"id": "2", "name": "Beatles"}]},
            ],
        }
    }

    # Expected output:
    # <subsonic-response ...>
    #   <indexes lastModified="123">
    #     <index name="A">
    #       <artist id="1" name="Abba"/>
    #     </index>
    #     <index name="B">
    #       <artist id="2" name="Beatles"/>
    #     </index>
    #   </indexes>
    # </subsonic-response>

    xml_output = dict_to_xml("subsonic-response", data)
    root = ET.fromstring(xml_output)

    # Check indexes element
    indexes = root.find("{http://subsonic.org/restapi}indexes")
    assert indexes is not None

    # Check children of indexes
    # Should have 2 'index' children directly
    index_nodes = indexes.findall("{http://subsonic.org/restapi}index")
    assert len(index_nodes) == 2, f"Expected 2 index nodes, found {len(index_nodes)}"

    assert index_nodes[0].get("name") == "A"
    assert index_nodes[1].get("name") == "B"


def test_boolean_lowercase():
    """Verify boolean values are lowercased."""
    data = {"system": {"online": True}}
    xml_output = dict_to_xml("subsonic-response", data)
    assert 'online="true"' in xml_output


def test_get_music_directory_structure():
    """Verify getMusicDirectory structure for nested lists."""
    data = {
        "directory": {
            "id": "1",
            "name": "Root",
            "child": [{"id": "10", "title": "Song 1", "isDir": False}, {"id": "11", "title": "Song 2", "isDir": True}],
        }
    }

    xml_output = dict_to_xml("subsonic-response", data)
    root = ET.fromstring(xml_output)
    directory = root.find("{http://subsonic.org/restapi}directory")

    # Check children - typical Subsonic calls them 'child' in the JSON schema,
    # but 'child' element in XML?
    # Actually Subsonic XML uses <child id="..." .../> for directory listings
    # OR specific types like <song> or <directory> depending on implementation.
    # But strictly, the schema usually says 'child' for generic directory entries.

    # My current overrides map in base.py doesn't have "child".
    # It attempts to derive from "child" -> "chil"?? Or just "child" (no 's').

    assert directory is not None
    children = directory.findall("{http://subsonic.org/restapi}child")
    assert len(children) == 2
    assert children[1].get("isDir") == "true"
