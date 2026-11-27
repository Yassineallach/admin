"""Excel shape layer: inject DrawingML shapes, live cell-linked text boxes and linked pictures into a saved .xlsx.

openpyxl can write charts but not shapes. This module adds, to one worksheet's drawing part:
  * rounded rectangles / ellipses with solid or gradient fill and a soft outer shadow
  * text boxes with static text, or with `textlink` (live text from a cell, exactly like Excel's =$A$1 shapes)
  * PNG pictures with an in-workbook hyperlink + tooltip (sidebar navigation)
Layers: "back" items are written before the charts (charts float above them), "front" items after.
Positions are given in pixels on the sheet and converted to two-cell anchors from the real column widths /
row heights, so every shape stays glued to its cells at any zoom level.

Google Sheets does not import Excel shapes, so callers only inject into the Excel edition.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

EMU = 9525
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_IMG = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
REL_LINK = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
REL_DRAWING = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing"


def col_px_list(ws, ncols):
    from openpyxl.utils import get_column_letter
    out = []
    for c in range(1, ncols + 1):
        w = ws.column_dimensions[get_column_letter(c)].width or 8.43
        out.append(int(7 * w + 0.49 + 1e-9))
    return out


def row_px_list(ws, nrows):
    return [round((ws.row_dimensions[r].height or 15) * 96 / 72) for r in range(1, nrows + 1)]


@dataclass
class Item:
    layer: str
    xml: str = ""
    picture: bytes | None = None
    link: str | None = None
    tooltip: str | None = None
    box: tuple = ()
    text: str | None = None
    textlink: str | None = None
    size: float = 11
    bold: bool = False


@dataclass
class Layer:
    cols: list
    rows: list
    font: str = "Arial"
    items: list = field(default_factory=list)
    _id: int = 1000

    # ---------------------------------------------------------------- geometry
    def _marker(self, px, sizes):
        acc = 0
        for i, s in enumerate(sizes):
            if px < acc + s or i == len(sizes) - 1:
                return i, max(0, int(px - acc))
            acc += s
        return len(sizes) - 1, 0

    def anchor(self, x0, y0, x1, y1, edit="absolute"):
        c0, co0 = self._marker(x0, self.cols)
        r0, ro0 = self._marker(y0, self.rows)
        c1, co1 = self._marker(x1, self.cols)
        r1, ro1 = self._marker(y1, self.rows)
        return (f'<xdr:twoCellAnchor editAs="{edit}"><xdr:from><xdr:col>{c0}</xdr:col><xdr:colOff>{co0 * EMU}</xdr:colOff>'
                f'<xdr:row>{r0}</xdr:row><xdr:rowOff>{ro0 * EMU}</xdr:rowOff></xdr:from><xdr:to><xdr:col>{c1}</xdr:col>'
                f'<xdr:colOff>{co1 * EMU}</xdr:colOff><xdr:row>{r1}</xdr:row><xdr:rowOff>{ro1 * EMU}</xdr:rowOff></xdr:to>')

    def x(self, col, off=0):
        return sum(self.cols[:col - 1]) + off

    def y(self, row, off=0):
        return sum(self.rows[:row - 1]) + off

    def nid(self):
        self._id += 1
        return self._id

    @staticmethod
    def _xfrm(x0, y0, x1, y1):
        return (f'<a:xfrm><a:off x="{int(x0 * EMU)}" y="{int(y0 * EMU)}"/>'
                f'<a:ext cx="{int((x1 - x0) * EMU)}" cy="{int((y1 - y0) * EMU)}"/></a:xfrm>')

    # ---------------------------------------------------------------- fills / effects
    @staticmethod
    def _fill(fill=None, grad=None, alpha=None):
        if grad:
            stops = "".join(f'<a:gs pos="{int(p * 1000)}"><a:srgbClr val="{c}"/></a:gs>' for p, c in grad[0])
            return f'<a:gradFill rotWithShape="1"><a:gsLst>{stops}</a:gsLst><a:lin ang="{grad[1] * 60000}" scaled="0"/></a:gradFill>'
        if fill is None:
            return "<a:noFill/>"
        a = f'<a:alpha val="{int(alpha * 1000)}"/>' if alpha is not None else ""
        return f'<a:solidFill><a:srgbClr val="{fill}">{a}</a:srgbClr></a:solidFill>'

    @staticmethod
    def _shadow(shadow):
        if not shadow:
            return "<a:effectLst/>"
        color, alpha, blur, dist = shadow
        return (f'<a:effectLst><a:outerShdw blurRad="{blur * EMU}" dist="{dist * EMU}" dir="5400000" algn="t" rotWithShape="0">'
                f'<a:srgbClr val="{color}"><a:alpha val="{int(alpha * 1000)}"/></a:srgbClr></a:outerShdw></a:effectLst>')

    # ---------------------------------------------------------------- shapes
    def shape(self, x0, y0, x1, y1, geom="roundRect", radius=0.12, fill="FFFFFF", grad=None, line=None, shadow=None,
              layer="back", name="Card", alpha=None):
        sid = self.nid()
        adj = f'<a:gd name="adj" fmla="val {int(radius * 100000)}"/>' if geom in ("roundRect",) else ""
        ln = f'<a:ln w="{int(line[1] * EMU)}"><a:solidFill><a:srgbClr val="{line[0]}"/></a:solidFill></a:ln>' if line else "<a:ln><a:noFill/></a:ln>"
        xml = (self.anchor(x0, y0, x1, y1) +
               f'<xdr:sp macro="" textlink=""><xdr:nvSpPr><xdr:cNvPr id="{sid}" name="{name} {sid}"/><xdr:cNvSpPr/></xdr:nvSpPr>'
               f'<xdr:spPr>{self._xfrm(x0, y0, x1, y1)}<a:prstGeom prst="{geom}"><a:avLst>{adj}</a:avLst></a:prstGeom>'
               f'{self._fill(fill, grad, alpha)}{ln}{self._shadow(shadow)}</xdr:spPr>'
               f'<xdr:txBody><a:bodyPr rtlCol="0" anchor="ctr"/><a:lstStyle/><a:p><a:endParaRPr lang="en-US" sz="1100"/></a:p></xdr:txBody>'
               f'</xdr:sp><xdr:clientData fLocksWithSheet="1" fPrintsWithSheet="1"/></xdr:twoCellAnchor>')
        self.items.append(Item(layer, xml, box=(x0, y0, x1, y1)))

    def text(self, x0, y0, x1, y1, text=None, textlink=None, size=11, bold=False, color="222222", align="l",
             anchor="ctr", layer="front", cached=""):
        """Text box. `textlink` = absolute same-sheet reference such as '$BV$5' (live text from that cell)."""
        sid = self.nid()
        algn = {"l": "l", "c": "ctr", "r": "r"}[align]
        rpr = (f'<a:rPr lang="en-US" sz="{int(size * 100)}" b="{1 if bold else 0}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
               f'<a:latin typeface="{self.font}"/><a:cs typeface="{self.font}"/></a:rPr>')
        if textlink:
            body = (f'<a:p><a:pPr algn="{algn}"/><a:fld id="{{{str(uuid.uuid4()).upper()}}}" type="TxLink">{rpr}'
                    f'<a:pPr algn="{algn}"/><a:t>{escape(str(cached))}</a:t></a:fld><a:endParaRPr lang="en-US" sz="{int(size * 100)}"/></a:p>')
            tl = textlink
        else:
            body = f'<a:p><a:pPr algn="{algn}"/><a:r>{rpr}<a:t>{escape(text)}</a:t></a:r></a:p>'
            tl = ""
        xml = (self.anchor(x0, y0, x1, y1) +
               f'<xdr:sp macro="" textlink="{tl}"><xdr:nvSpPr><xdr:cNvPr id="{sid}" name="Text {sid}"/><xdr:cNvSpPr txBox="1"/></xdr:nvSpPr>'
               f'<xdr:spPr>{self._xfrm(x0, y0, x1, y1)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
               f'<a:noFill/><a:ln><a:noFill/></a:ln></xdr:spPr>'
               f'<xdr:txBody><a:bodyPr vertOverflow="clip" horzOverflow="clip" wrap="none" lIns="0" tIns="0" rIns="0" bIns="0" '
               f'rtlCol="0" anchor="{anchor}"/><a:lstStyle/>{body}</xdr:txBody></xdr:sp>'
               f'<xdr:clientData fLocksWithSheet="1" fPrintsWithSheet="1"/></xdr:twoCellAnchor>')
        self.items.append(Item(layer, xml, box=(x0, y0, x1, y1), text=text, textlink=textlink, size=size, bold=bold))

    def picture(self, x0, y0, x1, y1, png: bytes, link_sheet: str | None = None, tooltip: str | None = None, layer="front"):
        self.items.append(Item(layer, picture=png, link=link_sheet, tooltip=tooltip, box=(x0, y0, x1, y1)))

    # ---------------------------------------------------------------- write
    def inject(self, path, sheet_title, cached_values=None):
        """Write the layer into `path` (in place). cached_values: {"$A$1": "text"} for text-linked boxes."""
        cached_values = cached_values or {}
        z = zipfile.ZipFile(path)
        files = {n: z.read(n) for n in z.namelist()}
        infos = {i.filename: i for i in z.infolist()}
        z.close()
        wbxml = files["xl/workbook.xml"].decode()
        rels = files["xl/_rels/workbook.xml.rels"].decode()
        m = re.search(r'<sheet [^>]*name="' + re.escape(escape(sheet_title, {'"': "&quot;"})) + r'"[^>]*r:id="(rId\d+)"', wbxml)
        rid = m.group(1)
        target = re.search(r'Id="' + rid + r'"[^>]*Target="([^"]+)"', rels) or re.search(r'Target="([^"]+)"[^>]*Id="' + rid + '"', rels)
        sheet_path = "xl/" + target.group(1).lstrip("/").replace("xl/", "")
        sheet_rels_path = sheet_path.replace("worksheets/", "worksheets/_rels/") + ".rels"
        srels = files[sheet_rels_path].decode()
        dm = re.search(r'Type="' + REL_DRAWING + r'"[^>]*Target="([^"]+)"', srels) or \
            re.search(r'Target="([^"]+)"[^>]*Type="' + REL_DRAWING + '"', srels)
        drawing_path = "xl/drawings/" + dm.group(1).split("/")[-1]
        drel_path = drawing_path.replace("drawings/", "drawings/_rels/") + ".rels"
        dxml = files[drawing_path].decode()
        drels = files.get(drel_path, b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                    b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>').decode()
        next_rel = max([int(x) for x in re.findall(r'Id="rId(\d+)"', drels)] + [0]) + 1
        back, front = [], []
        n_img = 0
        for it in self.items:
            if it.picture is not None:
                n_img += 1
                media = f"xl/media/shape_icon_{uuid.uuid4().hex[:12]}.png"
                files[media] = it.picture
                img_rid = f"rId{next_rel}"; next_rel += 1
                drels = drels.replace("</Relationships>", f'<Relationship Id="{img_rid}" Type="{REL_IMG}" Target="../media/{media.split("/")[-1]}"/></Relationships>')
                link = ""
                if it.link:
                    lrid = f"rId{next_rel}"; next_rel += 1
                    tgt = "#" + ("'" + it.link + "'" if " " in it.link or "-" in it.link else it.link) + "!A1"
                    drels = drels.replace("</Relationships>", f'<Relationship Id="{lrid}" Type="{REL_LINK}" Target="{escape(tgt)}"/></Relationships>')
                    tip = f' tooltip="{escape(it.tooltip or it.link, {chr(34): "&quot;"})}"' if (it.tooltip or it.link) else ""
                    link = f'<a:hlinkClick xmlns:r="{NS_R}" r:id="{lrid}"{tip}/>'
                pid = self.nid()
                x0, y0, x1, y1 = it.box
                it.xml = (self.anchor(x0, y0, x1, y1, edit="oneCell") +
                          f'<xdr:pic><xdr:nvPicPr><xdr:cNvPr id="{pid}" name="Icon {pid}" descr="{escape(it.tooltip or "")}">{link}</xdr:cNvPr>'
                          f'<xdr:cNvPicPr><a:picLocks noChangeAspect="1"/></xdr:cNvPicPr></xdr:nvPicPr>'
                          f'<xdr:blipFill><a:blip xmlns:r="{NS_R}" r:embed="{img_rid}"/><a:stretch><a:fillRect/></a:stretch></xdr:blipFill>'
                          f'<xdr:spPr>{self._xfrm(x0, y0, x1, y1)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr></xdr:pic>'
                          f'<xdr:clientData fLocksWithSheet="1" fPrintsWithSheet="1"/></xdr:twoCellAnchor>')
            xml = it.xml
            if it.textlink and it.textlink in cached_values:
                xml = re.sub(r"(<a:fld [^>]*>.*?<a:t>)(.*?)(</a:t>)", lambda mm: mm.group(1) + escape(str(cached_values[it.textlink])) + mm.group(3),
                             xml, count=1, flags=re.S)
            (back if it.layer == "back" else front).append(xml)
        # root may be <wsDr xmlns="..."> (openpyxl) or <xdr:wsDr ...> (Excel); declare the prefixes we use
        m_root = re.search(r"<(xdr:)?wsDr\b[^>]*>", dxml)
        root = m_root.group(0)
        new_root = root
        if 'xmlns:xdr="' not in root:
            new_root = new_root[:-1] + ' xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing">'
        if 'xmlns:a="' not in root:
            new_root = new_root[:-1] + f' xmlns:a="{NS_A}">'
        dxml = dxml.replace(root, new_root + "".join(back), 1)
        close = "</xdr:wsDr>" if m_root.group(1) else "</wsDr>"
        dxml = dxml.replace(close, "".join(front) + close)
        files[drawing_path] = dxml.encode()
        files[drel_path] = drels.encode()
        ct = files["[Content_Types].xml"].decode()
        if 'Extension="png"' not in ct:
            ct = ct.replace("<Default ", '<Default Extension="png" ContentType="image/png"/><Default ', 1)
            files["[Content_Types].xml"] = ct.encode()
        fd, tmp = tempfile.mkstemp(suffix=".xlsx")
        import os
        os.close(fd)
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
            order = ["[Content_Types].xml"] + [n for n in files if n != "[Content_Types].xml"]
            for n in order:
                out.writestr(infos.get(n, zipfile.ZipInfo(n)) if n in infos else n, files[n])
        shutil.move(tmp, path)

    def text_items(self):
        return [it for it in self.items if it.text is not None or it.textlink]
