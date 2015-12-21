import xml.etree.ElementTree as ET


class FxgToSvg:
    def __init__(self, path):
        rootAttr = {'xmlns': 'http://www.w3.org/2000/svg',
                    'version': '1.1',
                    'xmlns:xlink': 'http://www.w3.org/1999/xlink',
                    'preserveAspectRatio': "none",
                    'x': "0px",
                    'y': "0px",
                    'width': '720px',
                    'height': '900px',
                    'viewBox': '0 0 720 900'}
        self.svg_root = ET.Element('svg', rootAttr)
        self.fxg_root = ET.parse(path).getroot()
        self.name_key = []

    def parse_color(self, path_node):
        colors = []
        fill_node = path_node.find('./*')
        for node in fill_node.findall('./*'):
            print(ET.tostring(node))
            if self.remove_namespace(node.tag) == 'SolidColor':
                colors.append(node.attrib['color'])
            else:
                print(ET.tostring(node))
                raise Exception
        return colors

    @staticmethod
    def parse_transform(attribute):
        transform_string = ''
        if 'x' in attribute:
            transform_string += ' translate(%s %s)' % (attribute['x'], attribute['y'])
        if 'scaleX' in attribute:
            transform_string += ' scale(%s %s)' % (attribute['scaleX'], attribute['scaleY'])
        if 'rotation' in attribute:
            transform_string += ' rotate(%s)' % attribute['rotation']
        return transform_string

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
            if tag in ['Graphic', 'Library']:
                self.parse(fxg_child, svg_node)
            elif tag == 'Definition':
                name = fxg_child.attrib['name']
                if name is not None:
                    svg_child = ET.Element('defs')
                    self.parse(fxg_child,svg_child, name)
                    svg_node.append(svg_child)
                    self.name_key.append(name)
                    print('save %s' % name)
            elif tag == 'Group':
                svg_attrib = dict()
                if id is not None:
                    svg_attrib['id'] = id

                transform_string = self.parse_transform(fxg_child.attrib)
                if len(transform_string) > 0:
                    svg_attrib['transform'] = transform_string
                svg_child = ET.Element('g', svg_attrib)
                svg_node.append(svg_child)
                self.parse(fxg_child, svg_child)
            elif tag == 'Path':
                svg_attrib = dict()
                transform_string = self.parse_transform(fxg_child.attrib)
                path_string = ''
                if fxg_child.attrib['data']:
                    path_string = fxg_child.attrib['data']
                colors = self.parse_color(fxg_child)
                if len(transform_string)>0:
                    svg_attrib['transform'] = transform_string
                svg_attrib['d'] = path_string

                if len(colors) == 1:
                    svg_attrib['fill'] = colors[0]
                elif len(colors) > 1:
                    raise Exception

                svg_child = ET.Element('path', svg_attrib)
                svg_node.append(svg_child)
            elif tag in self.name_key:
                svg_attrib = dict()
                svg_attrib['xlink:href'] = '#' + tag
                transform_string = self.parse_transform(fxg_child.attrib)
                svg_attrib['transform'] = transform_string
                svg_child = ET.Element('use', svg_attrib)
                svg_node.append(svg_child)
            elif tag in ['Library', 'Definition']:
                continue
            else:
                print(tag)
        return

    def convert(self):
        self.parse(self.fxg_root, self.svg_root)
        return self.svg_root


f2s = FxgToSvg('fxg/input.fxg')
svg_xml = f2s.convert()
ET.ElementTree(svg_xml).write('svg/output.svg')
