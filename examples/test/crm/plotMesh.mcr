#!MC 1410
$!VarSet |MFBD| = '/home/john/hg/pysurf/test/crm'
$!PICK SETMOUSEMODE
  MOUSEMODE = SELECT
$!PAGE NAME = 'Untitled'
$!PAGECONTROL CREATE
$!PICK SETMOUSEMODE
  MOUSEMODE = SELECT
$!OPENLAYOUT  "./layout_mesh.lay"
$!PRINTSETUP PALETTE = COLOR
$!EXPORTSETUP IMAGEWIDTH = 1500
$!EXPORTSETUP USESUPERSAMPLEANTIALIASING = YES
$!EXPORTSETUP EXPORTFNAME = './images/image.png'
$!EXPORT
  EXPORTREGION = CURRENTFRAME
$!RemoveVar |MFBD|
