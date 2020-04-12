try:
    from lxml import etree
    import os
    import sys
    import logging
    import unittest
    from collections import defaultdict
except ImportError as e:
    logging.critical('Importing dependency failed with error: ' + str(e))


logging.basicConfig(
    filename='compare_xml.log',
    level=logging.INFO, filemode='w',
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
)

logger = logging.getLogger()
# Unittest module output should not overwrite logger output.
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


class Document:
    def __init__(self, form_id: str, contract_number: object, form: object):
        self.__form_id = form_id
        self.__contract_number = contract_number
        self.__form = form
        logger.debug('Created document: Form ID - {}, Contract Number - {}'.format(self.get_form_id(), self.get_contract_number()))

    def get_form_id(self):
        return self.__form_id

    def set_form_id(self, form_id):
        self.__form_id = form_id

    def get_contract_number(self):
        return self.__contract_number

    def set_contract_number(self, contract_number):
        self.__contract_number = contract_number

    def get_form(self):
        return self.__form

    def set_form(self, form):
        self.__form = form


class Parser:

    def parse_file(self, xml):
        parser = etree.XMLParser(remove_comments=True)
        return etree.parse(xml, parser)

    def get_children(self, tree):
        return list(tree.iter())

    def find_tag(self, root, tag_name):
        for tag in root.iter(tag_name):
            return tag

    def get_attribute(self, tag):
        return tag.attrib

    def find_tag_by_name(self, tree, tag: str):
        for location in tree.findall('.//' + tag):
            logger.debug('Tag located at: ' + location.tag)
            return location

    def find_tag_by_text(self, tree, tag: str):
        for location in tree.xpath('.//*[contains(text(),"{}")]'.format(tag)):
            logger.debug('Tag located at: ' + location.tag)
            return location

    def find_tag_by_attrib(self, tree, tag: str, attrib: str, value: str):
        for location in tree.xpath('.//{}[@{}={}]'.format(tag, attrib, value)):
            logger.debug('Tag located at: ' + location.tag)
            return location

    def get_parent_nodes(self, tree, node):
        root_children = self.get_children(tree)
        node_children = root_children.index(node) + 1
        # Remove all nodes below the current node.
        parent_nodes = root_children[:node_children]
        logger.debug('Parent nodes are: ' + str(parent_nodes))
        return parent_nodes

    def view_tree_levels(self, elem, func, level=0):
        """
        Recursive function that records the level of an element in the
        tree and prints the elements position.
        """
        func(elem, level)
        # todo: Replace getchildren.
        # todo: Test script should not alter xml document.
        for child in elem.getchildren():
            self.view_tree_levels(child, func, level+1)
            child.set('lvl', level)

    def print_level(self, elem, level):
        logger.debug(' '*level + '<' + elem.tag + '>')


class CompareXml(unittest.TestCase):
    # todo: These can be object properties.
    documents = dict()

    def get_document(self, index):
        return list(self.documents.items())[index][1]

    def get_tags(self, elements):
        tags = []
        for element in elements:
            tags.append(element.tag)
        return tags

    def get_texts(self, elements):
        texts = []
        for element in elements:
            texts.append(element.text)
        return texts

    def compare_form_id(self):
        try:
            self.assertEqual(self.get_document(0).get_form_id(), self.get_document(1).get_form_id())
            logger.debug('Form Ids match.')
        except AssertionError as e:
            logger.error('Form Ids do not match.\n' + str(e))
        else:
            return True

    def compare_contract_number(self):
        try:
            self.assertEqual(self.get_document(0).get_contract_number().text, self.get_document(1).get_contract_number().text)
            logger.debug('Contract numbers match.')
        except AssertionError as e:
            logger.error('Contract numbers do not match.\n' + str(e))
        else:
            return True

    def check_preconditions(self):
        if self.compare_form_id() and self.compare_contract_number():
            logger.info('Starting test suite for contract number ' + str(self.get_document(0).get_contract_number().text) + '\n')
        else:
            logger.error('Exiting test.')
            raise AssertionError

    # todo: No usage.
    def file_is_xml(self, file):
        try:
            file.endswith('.xml')
        except TypeError as e:
            logger.error('File is not in xml format.\n' + str(e))

    def localize_difference(self, form, tag):
        parent_nodes = self.parser.get_parent_nodes(form, tag)
        location = self.get_tags(parent_nodes)
        # Use list comprehension to make tags more readable.
        location = ['<' + tag_name + '>' for tag_name in location]
        # Remove list brackets.
        location = (', '.join(location))
        return location

    def report_tag_differences(self, diff: list, form, message):
        for i in range(len(diff)):
            difference = self.parser.find_tag_by_name(form, diff[i])
            location = self.localize_difference(form, difference)
            logger.info('{}: Tag located at {}\n'.format(message, location))

    def report_text_differences(self, diff: list, form, message):
        for i in range(len(diff)):
            difference = self.parser.find_tag_by_text(form, diff[i])
            location = self.localize_difference(form, difference)
            logger.info('{}: "{}" located at {}\n'.format(message, difference.text, location))

    # todo: Meaning of 0 and 1 unclear.
    def report_attribute_differences(self, diff: list, form, message):
        tag = diff[0]
        attribute = diff[1][0].keys()[0]
        value = diff[1][0].values()[0]
        difference = self.parser.find_tag_by_attrib(form, tag, attribute, value)
        location = self.localize_difference(form, difference)
        logger.info('{}: "{}" with attribute "{}" located at {}\n'.format(message, difference.tag, difference.attrib, location))

    def get_attributes(self, elements):
        attributes = defaultdict(list)
        for child in elements:
            if child.attrib:
                attributes[child.tag].append(child.attrib)
        logger.debug(attributes)
        return attributes

    @classmethod
    def setUpClass(cls):
        logger.debug('Parsing documents.')
        cls.parser = Parser()
        precondition = CompareXml()
        for file in os.listdir('data'):
            try:
                tree = cls.parser.parse_file('data/' + file)
                root = tree.getroot()
                form = cls.parser.find_tag(root, 'formular')
                form_id = str(cls.parser.get_attribute(form).get('id'))
                contract_number = cls.parser.find_tag(root, 'v_vertragsnummer')
                cls.documents[file] = Document(form_id, contract_number, root)
            except etree.ParseError as e:
                logger.error('File ' + file + ' cannot be parsed.\n' + str(e))
        precondition.check_preconditions()

    def retrieve_differences(self, list_prod, list_test):
        # Get all node tags.
        tags_prod = set(list_prod)
        tags_test = set(list_test)
        diff_prod_to_test = tags_prod.difference(tags_test)
        diff_prod_to_test = list(diff_prod_to_test)
        logger.debug('Difference texts prod -> test: ' + str(diff_prod_to_test))
        diff_test_to_prod = tags_test.difference(tags_prod)
        diff_test_to_prod = list(diff_test_to_prod)
        logger.debug('Difference texts test -> prod: ' + str(diff_test_to_prod))
        return [diff_prod_to_test, diff_test_to_prod]

    def test_tag_differences(self):
        logger.info('Checking xml files for differences in tags.\n')

        nodes_prod = self.parser.get_children(self.get_document(0).get_form())
        nodes_test = self.parser.get_children(self.get_document(1).get_form())

        tags_prod = self.get_tags(nodes_prod)
        tags_test = self.get_tags(nodes_test)

        diff = self.retrieve_differences(tags_prod, tags_test)

        if diff:
            self.report_tag_differences(diff[0], self.get_document(0).get_form(), 'Difference prod -> test')
            self.report_tag_differences(diff[1], self.get_document(1).get_form(), 'Difference test -> prod')
        else:
            logger.info('No differences between tags.')

    def test_text_differences(self):
        logger.info('Checking xml files for differences in text content.\n')
        nodes_prod = self.parser.get_children(self.get_document(0).get_form())
        nodes_test = self.parser.get_children(self.get_document(1).get_form())

        texts_prod = self.get_texts(nodes_prod)
        texts_test = self.get_texts(nodes_test)

        diff = self.retrieve_differences(texts_prod, texts_test)

        if diff:
            self.report_text_differences(diff[0], self.get_document(0).get_form(), 'Difference prod -> test')
            self.report_text_differences(diff[1], self.get_document(1).get_form(), 'Difference test -> prod')
        else:
            logger.info('No differences between texts.')

    def test_attribute_differences(self):
        logger.info('Checking xml files for differences in attributes.\n')
        nodes_prod = self.parser.get_children(self.get_document(0).get_form())
        nodes_test = self.parser.get_children(self.get_document(1).get_form())
        # Get elements that have an attribute.
        attributes_prod = self.get_attributes(nodes_prod)
        attributes_test = self.get_attributes(nodes_test)
        success = True
        for attrib_prod, attrib_test in zip(attributes_prod.items(), attributes_test.items()):
            try:
                self.assertEqual(attrib_prod, attrib_test)
            except AssertionError:
                success = False
                self.report_attribute_differences(attrib_prod, self.get_document(0).get_form(), 'Difference prod -> test')
                self.report_attribute_differences(attrib_test, self.get_document(1).get_form(), 'Difference test -> prod')
        if success:
            logger.info('No differences between attributes.\n')

# todo: User friendly report at INFO level.
# todo: Get document 0 and get document 1 -> Clarify meaning.


if __name__ == "__main__":
    unittest.main()
