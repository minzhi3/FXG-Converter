import xml.etree.ElementTree as ET


class FxgToSvg:
    def __init__(self, path):
        rootAttr = {'xmlns': 'http://www.w3.org/2000/svg',
                    'version': '1.1',
                    'xmlns:xlink': 'http://www.w3.org/1999/xlink',
                    'preserveAspectRatio': "none",
                    'x': "0px",
                    'y': "0px"}
        self.svg_root = ET.Element('svg', rootAttr)
        self.fxg_root = ET.parse(path).getroot()
        self.name_key = []
        self.symbols = dict()
        self.origin_name = dict()

    def parse_defines(self):
        for def_node in self.fxg_root.iter():
            tag = self.remove_namespace(def_node.tag)
            if tag == 'Definition':
                name = def_node.attrib['name']
                self.symbols[name] = list(def_node)
                if '{http://ns.adobe.com/flame/2008}originalName' in def_node.attrib:
                    self.origin_name[name] = def_node.attrib['{http://ns.adobe.com/flame/2008}originalName']
                else:
                    self.origin_name[name] = None
                print('save %s' % name)

    def parse_color(self, path_node):
        colors = []
        fill_node = path_node.find('./*')
        for node in fill_node.findall('./*'):
            if self.remove_namespace(node.tag) == 'SolidColor':
                colors.append(node.attrib['color'])
            else:
                raise Exception
        return colors

    @staticmethod
    def parse_attrib(attribute):
        result_attrib = dict()
        # Parse transform information
        transform_string = ''
        if 'x' in attribute or 'y' in attribute:
            x = attribute.get('x',0)
            y = attribute.get('y',0)
            transform_string += ' translate(%s %s)' % (x, y)
        if 'rotation' in attribute:
            transform_string += ' rotate(%s)' % attribute['rotation']
        if 'scaleX' in attribute or 'scaleY' in attribute:
            scale_x = attribute.get('scaleX',1)
            scale_y = attribute.get('scaleY',1)
            transform_string += ' scale(%s %s)' % (scale_x, scale_y)
        if len(transform_string) > 0:
            result_attrib['transform'] = transform_string

        # Parse alpha channel
        if 'alpha' in attribute:
            result_attrib['opacity'] = attribute['alpha']
        return result_attrib

    @staticmethod
    def remove_namespace(tag):
        if '}' in tag:
            return tag.split('}', 1)[1]
        else:
            return tag

    def parse(self, fxg_node, svg_node, id=None):
        print('parse %s %s' % (self.remove_namespace(fxg_node.tag), svg_node.tag))
        for fxg_child in fxg_node.findall("./*"):
            tag = self.remove_namespace(fxg_child.tag)
            if tag in ['Graphic']:
                self.parse(fxg_child, svg_node)
            elif tag in ['Definition', 'Library']:
                continue
            elif tag == 'Group':
                svg_attrib = dict()
                svg_attrib.update(self.parse_attrib(fxg_child.attrib))

                # Parse id
                if id is not None:
                    svg_attrib['id'] = id

                svg_child = ET.Element('g', svg_attrib)
                svg_node.append(svg_child)
                self.parse(fxg_child, svg_child)
            elif tag == 'Path':
                svg_attrib = dict()
                svg_attrib.update(self.parse_attrib(fxg_child.attrib))

                # Parse path data
                path_string = ''
                if fxg_child.attrib['data']:
                    path_string = fxg_child.attrib['data']
                svg_attrib['d'] = path_string

                # Parse color data
                colors = self.parse_color(fxg_child)
                if len(colors) == 1:
                    svg_attrib['fill'] = colors[0]
                elif len(colors) > 1:
                    raise Exception

                svg_child = ET.Element('path', svg_attrib)
                svg_node.append(svg_child)
            elif tag in self.symbols:
                print("parse %s" % tag)
                svg_attrib = dict()
                svg_attrib.update(self.parse_attrib(fxg_child.attrib))
                if tag not in self.symbols:
                    print(tag)
                    raise Exception

                symbol_node = self.symbols[tag]
                print("len of symbol_node %d" % len(symbol_node))
                if len(symbol_node) > 1 or len(svg_attrib) > 0:
                    svg_child = ET.Element('g', svg_attrib)
                    for symbol in symbol_node:
                        self.parse(symbol, svg_child)
                elif len(symbol_node) == 1:
                    temp_root = ET.Element('temp_root')
                    self.parse(symbol_node[0], temp_root)
                    svg_child = list(temp_root)[0]
                    svg_node.append(svg_child)
                if self.origin_name[tag]:
                    svg_child.attrib['class'] = self.origin_name[tag].replace(' ', '')
                    print(svg_child.attrib['class'])
                svg_node.append(svg_child)
            elif tag in ['Library', 'Definition']:
                continue
            else:
                print(tag)
        return

    def convert(self):
        self.parse_defines()
        self.parse(self.fxg_root, self.svg_root)
        return self.svg_root


f2s = FxgToSvg('fxg/star.fxg')
svg_xml = f2s.convert()
ET.ElementTree(svg_xml).write('svg/star.svg', encoding="UTF-8", xml_declaration=True)
