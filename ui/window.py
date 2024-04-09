import dearpygui.dearpygui as dpg

dpg.create_context()
# add a font registry
with dpg.font_registry():
    with dpg.font(r"ms.ttf", 16, tag="custom font"):
        dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
    dpg.bind_font(dpg.last_container())  # 最关键的一句

with dpg.window(label="Tutorial", height=400, width=400):
    with dpg.table(header_row=False, row_background=True, width=400,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True):

        # use add_table_column to add columns to the table,
        # table columns use child slot 0
        dpg.add_table_column()

        # add_table_next_column will jump to the next row
        # once it reaches the end of the columns
        # table next column use slot 1
        for i in range(0, 4):
            with dpg.table_row():
                for j in range(0, 3):
                    dpg.add_text(f"Row{i} Column{j}")

with dpg.window(label="", width=400, height=200, pos=(0, 400)):
    dpg.add_button(label="添加", callback=add_click)

with dpg.window(label="Logger", width=400, height=600, pos=(400, 0)):
    pass

if __name__ == '__main__':
    dpg.create_viewport(title='Custom Title', width=800, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
