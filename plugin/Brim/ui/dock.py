def find_item(root, type_name):
    prefix = type_name + "_QMLTYPE"
    pending = [root]
    while pending:
        item = pending.pop(0)
        name = item.metaObject().className()
        if name == type_name or name.startswith(prefix):
            return item
        pending.extend(item.childItems())
    return None
