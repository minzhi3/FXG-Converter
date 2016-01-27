import xml.etree.ElementTree as ET
import sys, getopt


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
        self.flm_ns = '{http://ns.adobe.com/flame/2008}'
        self.instance_types = ['no', 'graphic']

    def flm_full_name(self, name):
        return self.flm_ns + name

    def parse_defines(self):
        for def_node in self.fxg_root.iter():
            tag = self.remove_namespace(def_node.tag)
            if tag == 'Definition':
                symbol_type = def_node.attrib.get(self.flm_full_name('symbolType'), '0')
                name = def_node.attrib['name']

                self.symbols[(name, symbol_type)] = list(def_node)
                if self.flm_full_name('originalName') in def_node.attrib:
                    self.origin_name[(name, symbol_type)] = def_node.attrib[self.flm_full_name('originalName')]
                else:
                    self.origin_name[(name, symbol_type)] = None
                self.name_key.append(name)
                #print('save %s %s' % (name, symbol_type))

    def parse_path_style(self, path_node):
        style = dict()
        for style_node in path_node.findall('./*'):
            tag = self.remove_namespace(style_node.tag)
            if tag == 'fill':
                for node in style_node.findall('./*'):
                    if self.remove_namespace(node.tag) == 'SolidColor':
                        if 'fill' not in style:
                            style['fill'] = (node.attrib['color'])
                        else:
                            raise Exception
                    else:
                        print(node)
                        raise Exception
            elif tag == 'transform':
                transform_node = style_node.find('./*')
                if self.remove_namespace(transform_node.tag) == 'Transform':
                    transform_item = transform_node.find('./*')
                    transform_tag = self.remove_namespace(transform_item.tag)
                    if transform_tag == 'matrix':
                        if 'transform' not in style:
                            matrix_node = transform_item.find('./*')
                            style['transform'] = 'matrix(%s,%s,%s,%s,%s,%s)' % (
                                matrix_node.attrib['a'], matrix_node.attrib['b'], matrix_node.attrib['c'],
                                matrix_node.attrib['d'], matrix_node.attrib['tx'], matrix_node.attrib['ty'])
                        else:
                            raise Exception
                    elif transform_tag == 'colorTransform':
                        print('colorTransform')
                    else:
                        print(transform_item)
                        raise Exception
                else:
                    print(transform_node)
                    raise Exception
            else:
                print(tag)
                raise Exception

        return style

    @staticmethod
    def parse_attrib(attribute):
        result_attrib = dict()
        # Parse transform information
        transform_string = ''
        if 'x' in attribute or 'y' in attribute:
            x = attribute.get('x', 0)
            y = attribute.get('y', 0)
            transform_string += ' translate(%s %s)' % (x, y)
        if 'rotation' in attribute:
            transform_string += ' rotate(%s)' % attribute['rotation']
        if 'scaleX' in attribute or 'scaleY' in attribute:
            scale_x = attribute.get('scaleX', 1)
            scale_y = attribute.get('scaleY', 1)
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
        #print('parse %s %s' % (self.remove_namespace(fxg_node.tag), svg_node.tag))
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
                style = self.parse_path_style(fxg_child)
                if 'fill' in style:
                    svg_attrib['fill'] = style['fill']
                if 'transform' in style:
                    transform_string = svg_attrib.get('transform', '') + style['transform']
                    svg_attrib['transform'] = transform_string

                svg_child = ET.Element('path', svg_attrib)
                svg_node.append(svg_child)
            elif tag in self.name_key:
                svg_attrib = dict()
                svg_attrib.update(self.parse_attrib(fxg_child.attrib))
                instance_type = fxg_child.get(self.flm_full_name('instanceType'), 'no')
                symbol_type = str(self.instance_types.index(instance_type))

                #print("tag %s %s %s" % (tag, instance_type, symbol_type))
                if (tag, symbol_type) not in self.symbols:
                    print(tag)
                    raise Exception

                symbol_node = self.symbols[(tag, symbol_type)]
                #print("len of symbol_node %d" % len(symbol_node))
                if len(symbol_node) > 1 or len(svg_attrib) > 0:
                    svg_child = ET.Element('g', svg_attrib)
                    for symbol in symbol_node:
                        self.parse(symbol, svg_child)
                elif len(symbol_node) == 1:
                    temp_root = ET.Element('temp_root')
                    self.parse(symbol_node[0], temp_root)
                    svg_child = list(temp_root)[0]
                    svg_node.append(svg_child)
                if self.origin_name[(tag, symbol_type)]:
                    svg_child.attrib['class'] = self.origin_name[(tag, symbol_type)].replace(' ', '')
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


def main():
    if len(sys.argv) != 3:
        print("Usage: python fxg2svg.py <input file> <output file>")
        exit(2)
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    f2s = FxgToSvg(input_file)
    svg_xml = f2s.convert()
    ET.ElementTree(svg_xml).write(output_file, encoding="UTF-8", xml_declaration=False, method="xml")


if __name__ == "__main__":
    main()
