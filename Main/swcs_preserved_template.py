"""Generate an SWCS from the actual supplied workbook, preserving Excel drawings.

The original template's *blue operator-input cells only* are rewritten.
All drawing paths remain as user-editable reference objects and MUST be
adjusted manually in Excel to represent new timings accurately.

A standard OOXML package copy is used rather than rebuilding worksheets,
which avoids modifying the supplied diagram's line geometry/styles.
"""
from __future__ import annotations
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import math
import re
from xml.etree import ElementTree as E
from zipfile import ZipFile, ZIP_DEFLATED

TEMPLATE=Path(__file__).resolve().parent/'resources'/'HA_Stage_4_Nozzle_SWCS_template.xlsx'
M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
C='http://schemas.openxmlformats.org/package/2006/content-types'

# Preformatted rows of the six provided operator worksheets.
TOTAL_ROWS=(42,38,36,38,38,38)
BLUE_FONT_RGB='0070C0'



ORIGINAL_NAMESPACE_URIS={
    'mc':'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'x14ac':'http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac',
    'x15':'http://schemas.microsoft.com/office/spreadsheetml/2010/11/main',
    'x15ac':'http://schemas.microsoft.com/office/spreadsheetml/2010/11/ac',
    'xr':'http://schemas.microsoft.com/office/spreadsheetml/2014/revision',
    'xr2':'http://schemas.microsoft.com/office/spreadsheetml/2015/revision2',
    'xr3':'http://schemas.microsoft.com/office/spreadsheetml/2016/revision3',
    'xr6':'http://schemas.microsoft.com/office/spreadsheetml/2016/revision6',
    'xr10':'http://schemas.microsoft.com/office/spreadsheetml/2016/revision10',
}


def serialize_worksheet(root):
    """Keep mc:Ignorable prefixes valid after XML reserialization.

    Older Excel templates declare namespaces used only as *attribute text*.
    ElementTree does not automatically preserve those unused declarations.
    """
    E.register_namespace('','http://schemas.openxmlformats.org/spreadsheetml/2006/main')
    E.register_namespace('r',R)
    E.register_namespace('mc',ORIGINAL_NAMESPACE_URIS['mc'])
    E.register_namespace('xr',ORIGINAL_NAMESPACE_URIS['xr'])
    raw=E.tostring(root,encoding='utf-8',xml_declaration=True)
    ignorable=root.get(tag(ORIGINAL_NAMESPACE_URIS['mc'],'Ignorable'),'').split()
    if not ignorable:return raw
    start=raw.index(b'<',raw.index(b'?>')+2)
    end=raw.index(b'>',start)
    head=raw[start:end]
    added=b''
    for prefix in ignorable:
        if prefix in ORIGINAL_NAMESPACE_URIS and b'xmlns:'+prefix.encode()+b'=' not in head:
            added+=b' xmlns:'+prefix.encode()+b'="'+ORIGINAL_NAMESPACE_URIS[prefix].encode()+b'"'
    return raw[:end]+added+raw[end:]

def tag(ns,name):return f'{{{ns}}}{name}'


def text_time(t):
    if not t or float(t)<0.000001:return None
    s=f'{float(t):.2f}'.rstrip('0').rstrip('.')
    return f'{s} min'


def template_blue_styles(archive):
    root=E.fromstring(archive['xl/styles.xml'])
    fonts=root.find(tag(M,'fonts'))
    styles=root.find(tag(M,'cellXfs'))
    blue=set()
    for number,style in enumerate(styles):
        font=fonts[int(style.get('fontId','0'))]
        color=font.find(tag(M,'color'))
        if color is not None and color.get('rgb','').upper().endswith(BLUE_FONT_RGB):blue.add(number)
    return blue


def write_input_cell(root,coordinate,value,blue_styles):
    """Edit only existing blue-styled cells; never change fixed black fields."""
    data=root.find(tag(M,'sheetData'))
    coord=re.match(r'[A-Z]+(\d+)',coordinate)
    if not coord: raise ValueError(f'Invalid cell coordinate {coordinate}')
    rownum=int(coord.group(1))
    row=next((r for r in data if int(r.get('r'))==rownum),None)
    if row is None:raise ValueError(f'No template row {rownum}')
    cell=next((c for c in row if c.get('r')==coordinate),None)
    if cell is None:raise ValueError(f'No input cell {coordinate} in supplied template')
    if int(cell.get('s','0')) not in blue_styles:
        raise ValueError(f'{coordinate} is not an editable blue cell in supplied template')
    for child in list(cell):
        if child.tag in (tag(M,'v'),tag(M,'is'),tag(M,'f')):cell.remove(child)
    cell.attrib.pop('t',None)
    if value is None or value == '':return
    if isinstance(value,(int,float)) and math.isfinite(value):
        E.SubElement(cell,tag(M,'v')).text=str(value)
    else:
        cell.set('t','inlineStr')
        i=E.SubElement(cell,tag(M,'is'))
        t=E.SubElement(i,tag(M,'t'))
        t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
        t.text=str(value)


def editable_step_rows(root,blue_styles,totals_row):
    """Return precisely those template rows whose step inputs are blue."""
    cells={c.get('r'):int(c.get('s','0')) for c in root.findall('.//'+tag(M,'sheetData')+'/'+tag(M,'row')+'/'+tag(M,'c'))}
    return [r for r in range(12,totals_row,2)
            if all(cells.get(f'{col}{r}') in blue_styles for col in ('C','D','G','H','I'))]


def if_blue(root,coordinate,value,blue_styles):
    try:write_input_cell(root,coordinate,value,blue_styles)
    except ValueError as error:
        if value is not None:raise

def rewrite_sheet(root, op_id, sequence, scenario, totals_row,blue):
    def setv(coord,value):write_input_cell(root,coord,value,blue)
    line_name=str(scenario.get('line_name') or scenario.get('scenario_name') or '')
    frame=str(scenario.get('framesize') or scenario.get('part_name') or '')
    setv('CN3',op_id.upper());setv('CN6',op_id.upper())
    setv('CN4',line_name[:40]);setv('E4',line_name[:30]);setv('E5',frame[:35])
    setv('E7',str(scenario.get('part_name') or frame))
    if scenario.get('takt_time') is not None:
        setv('AR6',f"{float(scenario['takt_time']):g} Minutes")
    slots=editable_step_rows(root,blue,totals_row)
    for row in range(12,totals_row,2):
        for col in ('C','D','G','H','I'):if_blue(root,f'{col}{row}',None,blue)
        if_blue(root,f'I{row+1}',None,blue)
    for row,step in zip(slots,sequence):
        setv(f'C{row}',int(step['index']))
        setv(f'D{row}',str(step['description'])[:180])
        setv(f'G{row}',text_time(step['manual']))
        setv(f'H{row}',text_time(step['auto']))
        setv(f'I{row}',text_time(step['walk']))
    setv(f'G{totals_row}',text_time(sum(s['manual'] for s in sequence)) or '0 min')
    setv(f'I{totals_row}',text_time(sum(s['walk'] for s in sequence)) or '0 min')
    # Preserve black source labels while clearing the old blue waiting number.
    if totals_row+1 <= 43:
        try:setv(f'H{totals_row+1}',None)
        except ValueError:pass


def export_template_swcs_xlsx(scenario, operator_ids, planned_steps):
    if not TEMPLATE.is_file():raise FileNotFoundError('Missing resources/HA_Stage_4_Nozzle_SWCS_template.xlsx')
    with ZipFile(TEMPLATE) as z:
        archive={x.filename:z.read(x.filename) for x in z.infolist()}
    blue=template_blue_styles(archive)
    book=E.fromstring(archive['xl/workbook.xml'])
    booksheets=book.find(tag(M,'sheets'))
    bookrels=E.fromstring(archive['xl/_rels/workbook.xml.rels'])
    content=E.fromstring(archive['[Content_Types].xml'])
    refrel={x.get('Id'):x for x in bookrels}
    original=list(booksheets)
    if len(original)<6:raise ValueError('The expected six supplied SWCS worksheets are missing')
    next_id=max(int(x.get('sheetId','0')) for x in original)+1
    next_rid=max(int(x.get('Id')[3:]) for x in bookrels if x.get('Id','').startswith('rId'))+1

    # Each operator's tasks continue on another copy of the genuine template
    # whenever the original operator sheet runs out of printed rows.
    batches=[]
    for op_index,operator_id in enumerate(operator_ids):
        rows=planned_steps(scenario,operator_id)
        template_index=min(op_index,5)
        first_total=TOTAL_ROWS[template_index]
        source_xml=E.fromstring(archive[f'xl/worksheets/sheet{template_index+1}.xml'])
        first_count=len(editable_step_rows(source_xml,blue,first_total))
        batches.append((operator_id,rows[:first_count],template_index,first_total))
        rows=rows[first_count:]
        page=2
        while rows:
            capacity=len(editable_step_rows(E.fromstring(archive['xl/worksheets/sheet1.xml']),blue,TOTAL_ROWS[0]))
            batches.append((f'{operator_id} ({page})',rows[:capacity],0,TOTAL_ROWS[0]))
            rows=rows[capacity:];page+=1

    # Build a new workbook sheet list in output order, all sharing the source
    # Excel template's formatting and editable native drawing objects.
    for item in original:booksheets.remove(item)
    for idx,(opid,rows,source_idx,total) in enumerate(batches,1):
        model=original[source_idx]
        if idx<=6 and not any(b[0]==opid for b in batches[:idx-1]):
            # Preserve the source worksheet where possible.
            sheet_index=idx
        else:
            sheet_index=idx
        old_path=f'xl/worksheets/sheet{source_idx+1}.xml'
        root=E.fromstring(archive[old_path])
        rewrite_sheet(root,opid,rows,scenario,total,blue)
        path=f'xl/worksheets/sheet{sheet_index}.xml'
        archive[path]=serialize_worksheet(root)
        # Clone the template's drawings to keep editing independent per sheet.
        dr=f'xl/drawings/drawing{source_idx+1}.xml'
        dn=f'xl/drawings/drawing{sheet_index}.xml'
        archive[dn]=archive[dr]
        sr=f'xl/worksheets/_rels/sheet{source_idx+1}.xml.rels'
        rel_root=E.fromstring(archive[sr])
        for rel in rel_root:
            if rel.get('Type','').endswith('/drawing'):
                rel.set('Target',f'../drawings/drawing{sheet_index}.xml')
        archive[f'xl/worksheets/_rels/sheet{sheet_index}.xml.rels']=E.tostring(rel_root,encoding='utf-8',xml_declaration=True)
        template=deepcopy(model)
        template.set('name',opid[:31]);template.set('sheetId',str(next_id));next_id+=1
        rid=f'rId{next_rid}';next_rid+=1
        template.set(tag(R,'id'),rid)
        booksheets.append(template)
        for part,ctype in [(f'/xl/worksheets/sheet{sheet_index}.xml',
                             'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'),
                            (f'/xl/drawings/drawing{sheet_index}.xml',
                             'application/vnd.openxmlformats-officedocument.drawing+xml')]:
            if not any(x.get('PartName')==part for x in content):
                E.SubElement(content,tag(C,'Override'),{'PartName':part,'ContentType':ctype})
    # Drop orphaned original drawings / worksheets and their relationships.
    for rid,rel in list(refrel.items()):
        if rel.get('Type','').endswith('/worksheet'):
            bookrels.remove(rel)
    for k in list(archive):
        match=re.fullmatch(r'xl/worksheets/(?:_rels/)?sheet(\d+)\.xml(?:\.rels)?',k)
        drawing=re.fullmatch(r'xl/drawings/drawing(\d+)\.xml',k)
        if (match or drawing) and int((match or drawing).group(1))>len(batches):
            archive.pop(k)
    # Keep only relationships to the new list of sheets. Restore them from the
    # freshly allocated sequential relationship IDs.
    for i,sheet in enumerate(booksheets,1):
        E.SubElement(bookrels,tag(P,'Relationship'),{'Id':sheet.get(tag(R,'id')),
            'Type':'http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet',
            'Target':f'worksheets/sheet{i}.xml'})
    for x in list(content):
        if x.get('PartName','').startswith(('/xl/worksheets/sheet','/xl/drawings/drawing')):
            number=re.search(r'(?:sheet|drawing)(\d+)\.xml$',x.get('PartName',''))
            if number and int(number.group(1))>len(batches):content.remove(x)
    E.register_namespace('',M);E.register_namespace('r',R)
    archive['xl/workbook.xml']=serialize_worksheet(book)
    E.register_namespace('',P)
    archive['xl/_rels/workbook.xml.rels']=E.tostring(bookrels,encoding='utf-8',xml_declaration=True)
    E.register_namespace('',C)
    archive['[Content_Types].xml']=E.tostring(content,encoding='utf-8',xml_declaration=True)
    result=BytesIO()
    with ZipFile(result,'w',ZIP_DEFLATED) as out:
        for name,data in archive.items():out.writestr(name,data)
    result.seek(0)
    return result
