# Import needed libraries
import pandas as pd
from rdflib import Graph, URIRef, RDFS, OWL, BNode


# Define functions
def parse_ontology(ontology_path):
    graph = Graph()
    try:
        graph.parse(ontology_path, format='xml')
    except Exception as e:
        print(f"Failed to parse the ontology: {e}")
        return None
    return graph


def get_class_properties(graph, class_iri, parent_iri=None):
    if graph is None:
        print("Invalid graph!")
        return {}

    class_uri = URIRef(class_iri)
    properties = {}

    # Look for any property where domain is the class
    for property_uri, _, _ in graph.triples((None, RDFS.domain, class_uri)):
        range_uri = None
        for _, _, r in graph.triples((property_uri, RDFS.range, None)):
            range_uri = str(r).split('/')[-1]
        properties[str(property_uri).split('/')[-1]] = (str(parent_iri or class_iri).split('/')[-1], 'property',
                                                        None, range_uri)

    # Look for any property where class is the range
    for property_uri, _, range_uri in graph.triples((None, RDFS.range, class_uri)):
        properties[str(property_uri).split('/')[-1]] = (str(parent_iri or class_iri).split('/')[-1], 'class relation',
                                                        str(range_uri).split('/')[-1], None)

    # Look for any OWL restriction on the class
    for _, _, restriction in graph.triples((class_uri, RDFS.subClassOf, None)):
        if isinstance(restriction, BNode):
            # We found a blank node, look for an onProperty relation
            for _, _, property_uri in graph.triples((restriction, OWL.onProperty, None)):
                range_uri = None
                for _, _, r in graph.triples((property_uri, RDFS.range, None)):
                    range_uri = str(r).split('/')[-1]
                for _, _, datatype in graph.triples((restriction, OWL.allValuesFrom, None)):
                    range_uri = str(datatype).split('/')[-1]
                properties[str(property_uri).split('/')[-1]] = (str(parent_iri or class_iri).split('/')[-1],
                                                                'property', None, range_uri)

    # Check the superclass(es) for properties
    for _, _, superclass in graph.triples((class_uri, RDFS.subClassOf, None)):
        if isinstance(superclass, URIRef):
            properties.update(get_class_properties(graph, str(superclass), class_iri))

    return properties


# Specify ontology file path and class IRI
# Attention: The OWL-File needs to be formatted as XML-RDF for this script!
ontology_path = "ebucoreplus_xml-rdf.owl"
class_iri = 'http://www.ebu.ch/metadata/ontologies/ebucoreplus#Brand'

# Load the ontology from a file
graph = parse_ontology(ontology_path)
if graph is None:
    exit(1)

# Get properties of the class
properties = get_class_properties(graph, class_iri)

# Convert to a Pandas DataFrame
df = pd.DataFrame.from_dict(properties, orient='index',
                            columns=['Inherited From', 'Relation Type', 'Points To', 'Data Type'])
df.index.name = 'Property'

# Save the DataFrame as an Excel file
class_name = class_iri.split('#')[-1]
df.to_excel(f"{class_name}_properties.xlsx")
