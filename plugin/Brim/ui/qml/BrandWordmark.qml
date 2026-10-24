import QtQuick 2.7

Image {
    property bool dark: true

    height: 16
    width: height * 237 / 90
    source: dark ? "brand/wordmark-dark.svg" : "brand/wordmark-light.svg"
    sourceSize.width: width * 2
    sourceSize.height: height * 2
    fillMode: Image.PreserveAspectFit
    smooth: true
    mipmap: true
}
