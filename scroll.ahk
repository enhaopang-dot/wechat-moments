#Requires AutoHotkey v2.0
; 拖拽微信朋友圈滚动条
; 用法: AutoHotkey64.exe scroll.ahk <x> <y> <distance>

x := A_Args[1]
y := A_Args[2]
distance := A_Args[3]

if (!x || !y || !distance) {
    MsgBox("用法: AutoHotkey64.exe scroll.ahk <x> <y> <distance>")
    ExitApp(1)
}

; 移动鼠标到滚动条位置（速度30ms）
MouseMove(x, y, 30)
Sleep(200)

; 按住左键拖拽向下
MouseClickDrag("L", x, y, x, y + distance, 50)
Sleep(200)

ExitApp(0)
