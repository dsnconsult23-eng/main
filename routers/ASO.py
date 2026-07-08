import platform
import jaydebeapi
import platform,sys
import math
import os 
from os.path import basename
import locale
from routers import Connection



import  openpyxl
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string
from copy import copy
import platform,sys,os,subprocess,codecs
from openpyxl.styles import Font, PatternFill, Alignment

class PisIpodatoci:
    def __init__(self, iznos,sheet,red,kolona):
        self.iznos=iznos
        self.sheet=sheet        
        self.red=red
        self.kolona=kolona

def Directories(m,g):
    if platform.system() == "Windows":
        sep="\\"
        configDIR="c:\\Anakonda\\PyInsurance"        
        inputDIR="C:\\Pregledi\\"+m+"_"+str(g)     
    else:
        sep="/"
        configDIR="/opt/siglife-reporting/"        
        inputDIR="/opt/siglife-reporting/ASO/"+m+"_"+str(g)      
    return configDIR,inputDIR,sep
    
def prebSI(mesec, godina):
    sql = f"{{call os_stat_izvestaj ('{mesec}','{godina}')}}"
    results, OK = Connection.OSISinit()
    if not OK:
        return False, "Nema vrskа so baza"
    results.execute(sql)
    rez = results.fetchone()
    podatoci = []
    zaPectanje = []
    return True, rez  # return True and the fetched row


from openpyxl.utils import get_column_letter

def utBaraj(podatoci, sheet, start_row=1, columns_per_row=3):
    """
    Processes a tuple (`podatoci`) and writes its elements in successive Excel cells.
    Distributes the elements across columns and rows in a grid pattern.

    Args:
        podatoci: Tuple containing data to process.
        sheet: The sheet number or name in the Excel workbook.
        start_row: The starting row for the cells (default is 1).
        columns_per_row: Number of columns per row (default is 3).

    Returns:
        zaPectanje: List of PisIpodatoci instances with the processed data.
    """
    zaPectanje = []
    current_row = start_row
    data_index = 0  # Track the index of the current data item

    # Loop through `podatoci` in the desired grid pattern
    while data_index < len(podatoci):
        for col_idx in range(1, columns_per_row + 1):  # Columns: A, B, C, etc.
            if data_index >= len(podatoci):  # Stop if all data is processed
                break

            # Get the next cell reference
            column_letter = get_column_letter(col_idx)
            kelija = f"{column_letter}{current_row}"

            # Create a PisIpodatoci object for each item in `podatoci`
            data_item = podatoci[data_index]  # Get the current data item
            re, ko = openpyxl.utils.cell.coordinate_to_tuple(kelija)
            novpodatok = PisIpodatoci(data_item, sheet, re, ko)
            zaPectanje.append(novpodatok)

            data_index += 1  # Move to the next data item

        current_row += 1  # Move to the next row

    # Print the results in the desired format
    for item in zaPectanje:
        print(f"Iznos: {item.iznos}, Sheet: {item.sheet}, Row: {item.red}, Column: {item.kolona}")

    return zaPectanje


def genSI(mesec, godina):
    sql = f"""
    SELECT vid_stavka, kol100, kol102, kol103, kol104, kol105, kol106, kol107,
           kol200, kol201, kol202, kol203, kol204, kol205, kol206, kol207
    FROM stat_izvestai
    WHERE stat_izvestaj='SP-1' 
      AND datum = LAST_DAY(mdy({mesec}, 1, {godina})) and  vid_stavka not  in ('19','190101','190201','190202','0000')
    order by stat_izvestaiid
    """

    print(sql)
    results, OK = Connection.OSISinit()
    if not OK:
        print("Greska - nema vrska so baza")
        return OK, 0.0, "Greska - nema vrska so baza"

    # Execute SQL query and fetch results
    results.execute(sql)  
    podatoci = []
    
    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)
    
    results.close()
    
    # Assume all data needs to be written into a single sheet
    sheet = 18  # Fixed sheet number
    return True, podatoci, "Vo red e"

    
import os
from shutil import copyfile
import openpyxl

def ImportSI(mesec, godina):
    # File handling
    mu1 = "statisticki_obrasci.xlsx"
    configDIR, inputDIR, sep = Directories(str(mesec), str(godina))
    mustra1 = os.path.join(configDIR, mu1)

    if not os.path.isfile(mustra1):
        greska = f"GRESKA: Ne postoi {mustra1}"
        return False, greska

    mu12 = f"statisticki_obrasci{mesec}-{godina}.xlsx"
    fileOUT = os.path.join(inputDIR, mu12)

    if os.path.isfile(mustra1):       
        try:
            copyfile(mustra1, fileOUT)
        except Exception as e:
            greska = f"Mora da ja zatvorite {fileOUT} i pokusajte povtorno: {str(e)}"
            return False, greska

    OK, podatoci, msg = genSI(mesec, godina)
    if not OK:
        return OK, msg

    # Write `podatoci` to Excel
    try:
        wb = openpyxl.load_workbook(fileOUT)
        sheet = wb.worksheets[17]  # 18th sheet (index 17)
        
        # Write data starting from row 13 and column C
        start_row = 13
        start_column = 3  # C corresponds to index 3
        
        for row_offset, row_data in enumerate(podatoci):
            cell_row = start_row + row_offset
            if cell_row in (14, 21,25,30,31,37,53):
                continue
            print (cell_row) 
            for col_offset, value in enumerate(row_data[1:], start=0):  # Skip `vid_stavka`
                
                cell_column = start_column + col_offset
                if (cell_row == 20 and cell_column in (6, 7)) or (cell_row == 21 and cell_column in (6, 7)) or (cell_row == 22 and cell_column in (6, 7)) or (cell_row == 23 and cell_column in (6, 7)) or (cell_row == 24 and cell_column in (6, 7)) or (cell_row == 25 and cell_column in (6, 7)):
                    continue
                if (cell_row == 37 and cell_column in (6, 7)) or (cell_row == 38 and cell_column in (6, 7)) or (cell_row == 39 and cell_column in (6, 7)) or (cell_row == 40 and cell_column in (6, 7)) or (cell_row == 41 and cell_column in (6, 7)) or (cell_row == 42 and cell_column in (6, 7)):
                    continue
                #if value is not None:
                sheet.cell(row=cell_row, column=cell_column, value=value)
        
        wb.save(fileOUT)
    except Exception as e:
        greska = f"GRESKA: Ne mozhe da se zapise vo {fileOUT}: {str(e)}"
        return False, greska

    return True, "\n\nRezultat zapisan vo "+fileOUT
    
def ImportSP1(mesec, godina):
    mu1 = "statisticki_obrasci.xlsx"
    configDIR, inputDIR, sep = Directories(str(mesec), str(godina))
    mustra1 = os.path.join(configDIR, mu1)

    if not os.path.isfile(mustra1):
        greska = f"GRESKA: Ne postoi {mustra1}"
        return False, greska

    mu12 = f"statisticki_obrasci{mesec}-{godina}.xlsx"
    fileOUT = os.path.join(inputDIR, mu12)

    if os.path.isfile(mustra1):       
        try:
            copyfile(mustra1, fileOUT)
        except Exception as e:
            greska = f"Mora da ja zatvorite {fileOUT} i pokusajte povtorno: {str(e)}"
            return False, greska
    # Define the custom order for `vid_stavka`
    custom_order = [
        "19010101", "19010102", "19010103", "19010104", "19010105",
        "190102", "19010201", "19010202", "19010203", "19010204", "19010205",
        "190103", "19010301", "19010302", "19010399",
        "19020101", "19020102", "19020103", "19020104", "19020105",
        "19020201", "19020202", "19020203", "19020204", "19020205",
        "190203", "19020301", "19020302", "19020399",
        "20", "21", "22", "23", "24", "25"
    ]

    # Fetch data
    sql = (
        "SELECT vid_stavka, kol100, kol102, kol103, kol104, kol105, kol106, "
        "kol107, kol200, kol201, kol202, kol203, kol204, kol205, kol206, kol207 "
        "FROM stat_izvestai "
        "WHERE stat_izvestaj = 'SP-1' and  vid_stavka not  in ('19','190101','190201','190202','0000') AND datum = LAST_DAY(mdy({},1,{}))".format(mesec, godina) 
    )

    print(sql)
    results, OK = Connection.OSISinit()
    if not OK:
        return False, "Greska - nema vrska so baza"

    results.execute(sql)

    podatoci = []
    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)

    results.close()

    # Filter and sort data
    filtered_data = [row for row in podatoci if row[0] in custom_order]
    filtered_data.sort(key=lambda x: custom_order.index(x[0]))

    # Write to Excel
    try:
        wb = openpyxl.load_workbook(fileOUT)
        sheet = wb.worksheets[17]  # 18th sheet (index 17)

        start_row = 13
        start_column = 3  # Start from column C

        for row_offset, row_data in enumerate(filtered_data):
            cell_row = start_row + row_offset

            # Skip specific rows or columns
            if (cell_row == 20 and cell_column in (6, 7)) or (cell_row == 21 and cell_column in (6, 7)) or (cell_row == 22 and cell_column in (6, 7)) or (cell_row == 23 and cell_column in (6, 7)) or (cell_row == 24 and cell_column in (6, 7)) or (cell_row == 25 and cell_column in (6, 7)):
                continue
            if (cell_row == 37 and cell_column in (6, 7)) or (cell_row == 38 and cell_column in (6, 7)) or (cell_row == 39 and cell_column in (6, 7)) or (cell_row == 40 and cell_column in (6, 7)) or (cell_row == 41 and cell_column in (6, 7)) or (cell_row == 42 and cell_column in (6, 7)):
                continue

            for col_offset, value in enumerate(row_data[1:], start=0):  # Skip `vid_stavka`
                cell_column = start_column + col_offset
                sheet.cell(row=cell_row, column=cell_column, value=value)

        wb.save(fileOUT)
    except Exception as e:
        return False, f"GRESKA: Ne mozhe da se zapise vo fajlot: {str(e)}"

    return True, "Podatocite se zapisani uspesno."


def ImportSISp11(mesec, godina):
    # Define directories and file paths
    mu1 = "statisticki_obrasci.xlsx"
    configDIR, inputDIR, sep = Directories(str(mesec), str(godina))
    print(mu1, configDIR, inputDIR)
    mustra1 = os.path.join(configDIR, mu1)
    print(mustra1)

    if not os.path.isfile(mustra1):                                                                                                       
        greska = f"GRESKA: Ne postoi {mustra1}"
        return False, greska

    mu12 = f"statisticki_obrasci{mesec}-{godina}.xlsx"
    print(mu12)
    fileOUT = os.path.join(inputDIR, mu12)

    if os.path.isfile(mustra1):       
        try: 
            copyfile(mustra1, fileOUT)
        except:
            greska = f"\n\nMora da ja zatvorite {fileOUT} i pokusajte povtorno"
            return False, greska

    # Generate the data to be written to the Excel file
    OK, podatoci, rez = genSI(mesec, godina) 
    if not OK:
        return OK, rez

    # Define rows to skip and vid_stavka to cell mapping
    rows_to_skip = {14,  26, 31, 43, 53}
    row_column_to_skip = {(20, 6), (20, 7), (21, 6), (21, 7),
                          (22, 6), (22, 7), (23, 6), (23, 7),
                          (24, 6), (24, 7), (25, 6), (25, 7),
                          (37, 6), (37, 7), (38, 6), (38, 7),
                          (39, 6), (39, 7), (40, 6), (40, 7),
                          (41, 6), (41, 7), (42, 6), (42, 7)}

    # Mapping vid_stavka to specific rows
    vid_stavka_mapping = {
        '1901': 13, '19010101': 15, '19010102': 16, '19010103': 17, '19010104': 18, '19010105': 19,
        '190102':20, '19010201': 21, '19010202': 22, '19010203': 23, '19010204': 24,
        '19010205': 25, '190103': 26, '19010301': 27, '19010302': 28, '19010399': 29, '1902': 30, 
        '19020101': 32, '19020102': 33, '19020103': 34, '19020104': 35, '19020105': 36,
        '19020201': 38, '19020202': 39, '19020203': 40, '19020204': 41, '19020205': 42,
        '190203': 43, '19020301': 44, '19020302': 45, '19020399': 46,
        '20': 47, '21': 48, '22': 49, '23': 50, '24': 51, '25': 52
    }

    try:
        # Open the Excel file
        wb = openpyxl.load_workbook(fileOUT)
        sheet = wb.worksheets[17]  # Select the desired sheet by index or name

        for row in podatoci: 
            vid_stavka = row[0]
            if vid_stavka in vid_stavka_mapping:
                target_row = vid_stavka_mapping[vid_stavka]
                start_column = 3  # Start writing from column C

                for col_offset, value in enumerate(row[1:]):  # Skip vid_stavka (index 0)
                    cell_column = start_column + col_offset
                    cell_row = target_row

                    # Skip specific rows or row-column pairs
                    if cell_row in rows_to_skip or (cell_row, cell_column) in row_column_to_skip:
                        continue

                    # Write value if not None
                    if value is not None:
                        sheet.cell(row=cell_row, column=cell_column, value=value)
        #SP-2
        sql = (
        "SELECT vid_stavka, kol100, kol200 ,"
         "kol200a, kol201, kol202, kol203, kol204, kol205, kol205a, kol206, kol300, kol301,kol302 "
        "FROM stat_izvestai "
        "WHERE stat_izvestaj = 'SP-2'   and  vid_stavka not  in ('19','190101','1902','190201','190202','0000') AND datum = LAST_DAY(mdy({},1,{}))".format(mesec, godina) 
        )


        print(sql)
        results, OK = Connection.OSISinit()
        if not OK:
            return False, "Greska - nema vrska so baza za Sp-2"

        results.execute(sql)

        podatoci = []
        while True:
            row = results.fetchone()
            if not row:
                break
            podatoci.append(row)
        rows_to_skip = {14, 21, 25, 30, 31, 37, 53}
        row_column_to_skip = {(16, 5), (16, 9), (16, 13),  (19, 5), (19, 9), (19, 13),
                              (20, 5), (20, 9), (20, 13), (21, 5), (21, 9), (21, 13),
                              (22, 5), (22, 9), (22, 13), (23, 5), (23, 9), (23, 13),
                              (24, 5), (24, 9), (24, 13),  (25, 5), (25, 9), (25, 13),
                              (26, 4), (26, 6), (26, 7), (26, 9), (26, 12),
                              (27, 4), (27, 6), (27, 7), (27, 9), (27, 12),
                              (28, 4), (28, 6), (28, 7), (28, 9), (28, 12),
                              (29, 4), (29, 6), (29, 7), (29, 9), (29, 12),
                              (33, 5), (33, 9), (33, 13),(36, 5), (36, 9), (36, 13),
                              (38, 5), (38, 9), (38, 13), (39, 5), (39, 9), (39, 13),
                              (40, 5), (40, 9), (40, 13),(41, 5), (41, 9), (41, 13),
                              (42, 5), (42, 9), (42, 13),
                              (43, 4), (43, 6), (43, 7), (43, 9), (43, 12),
                              (44, 4), (44, 6), (44, 7), (44, 9), (44, 12),
                              (45, 4), (45, 6), (45, 7), (45, 9), (45, 12),
                              (46, 4), (46, 6), (46, 7), (46, 9), (46, 12)}

        # Mapping vid_stavka to specific rows
        vid_stavka_mapping = {
            '19010101': 15, '19010102': 16, '19010103': 17, '19010104': 18, '19010105': 19,
            '190102':20, '19010201': 21, '19010202': 22, '19010203': 23, '19010204': 24,
            '19010205': 25, '190103': 26, '19010301': 27, '19010302': 28, '19010399': 29,
            '19020101': 32, '19020102': 33, '19020103': 34, '19020104': 35, '19020105': 36,
            '19020201': 38, '19020202': 39, '19020203': 40, '19020204': 41, '19020205': 42,
            '190203': 43, '19020301': 44, '19020302': 45, '19020399': 46,
            '20': 47, '21': 48, '22': 48, '23': 49, '24': 50, '25': 51
        }

        sheet = wb.worksheets[18]  

        for row in podatoci: 
            vid_stavka = row[0]
            if vid_stavka in vid_stavka_mapping:
                target_row = vid_stavka_mapping[vid_stavka]
                start_column = 3  # Start writing from column C

                for col_offset, value in enumerate(row[1:]):  # Skip vid_stavka (index 0)
                    cell_column = start_column + col_offset
                    cell_row = target_row

                    # Skip specific rows or row-column pairs
                    if cell_row in rows_to_skip or (cell_row, cell_column) in row_column_to_skip:
                        continue

                    # Write value if not None
                    if value is not None:
                        sheet.cell(row=cell_row, column=cell_column, value=value)
            
        #-----#SP-2-------------------  
        #SP-3
        sql = (
        "SELECT vid_stavka, kol100,kol101,kol102, kol200 ,"
         " kol300, kol301 "
        "FROM stat_izvestai "
        "WHERE stat_izvestaj = 'SP-3'   and  vid_stavka not  in ('19','190101','1902','190201','190202','0000') AND datum = LAST_DAY(mdy({},1,{}))".format(mesec, godina) 
        )


        print(sql)
        results, OK = Connection.OSISinit()
        if not OK:
            return False, "Greska - nema vrska so baza za Sp-3"

        results.execute(sql)

        podatoci = []
        while True:
            row = results.fetchone()
            if not row:
                break
            podatoci.append(row)
        rows_to_skip = {14, 21, 25, 30, 31, 37, 53}
        row_column_to_skip = {(21, 6), (22, 6), (23, 6),  (24, 6),
                              (38, 6),  (39, 6) , (40, 6),(41, 6)}

        # Mapping vid_stavka to specific rows
        vid_stavka_mapping = {
            '19010101': 15, '19010102': 16, '19010103': 17, '19010104': 18, '19010105': 19,
            '190102':20, '19010201': 21, '19010202': 22, '19010203': 23, '19010204': 24,
            '19010205': 25, '190103': 26, '19010301': 27, '19010302': 28, '19010399': 29,
            '19020101': 32, '19020102': 33, '19020103': 34, '19020104': 35, '19020105': 36,
            '19020201': 38, '19020202': 39, '19020203': 40, '19020204': 41, '19020205': 42,
            '190203': 43, '19020301': 44, '19020302': 45, '19020399': 46,
            '20': 47, '21': 48, '22': 48, '23': 49, '24': 50, '25': 51
        }

        sheet = wb.worksheets[20]  

        for row in podatoci: 
            vid_stavka = row[0]
            if vid_stavka in vid_stavka_mapping:
                target_row = vid_stavka_mapping[vid_stavka]
                start_column = 3  # Start writing from column C

                for col_offset, value in enumerate(row[1:]):  # Skip vid_stavka (index 0)
                    cell_column = start_column + col_offset
                    cell_row = target_row

                    # Skip specific rows or row-column pairs
                    if cell_row in rows_to_skip or (cell_row, cell_column) in row_column_to_skip:
                        continue

                    # Write value if not None
                    if value is not None:
                        sheet.cell(row=cell_row, column=cell_column, value=value)
            
        #-----#SP-3-------------------  
        #SP-4
        sql = (
        "SELECT vid_stavka, kol100,kol101,kol102, kol103,kol104 ,"
         " kol105, kol106, kol107 "
        "FROM stat_izvestai "
        "WHERE stat_izvestaj = 'SP-4'   and  vid_stavka not  in ('19','190101','1902','190201','190202','0000') AND datum = LAST_DAY(mdy({},1,{}))".format(mesec, godina) 
        )


        print(sql)
        results, OK = Connection.OSISinit()
        if not OK:
            return False, "Greska - nema vrska so baza za Sp-4"

        results.execute(sql)

        podatoci = []
        while True:
            row = results.fetchone()
            if not row:
                break
            podatoci.append(row)
        rows_to_skip = {14, 21, 25, 30, 31, 37, 53}
        row_column_to_skip = {}

        # Mapping vid_stavka to specific rows
        vid_stavka_mapping = {
            '19010101': 15, '19010102': 16, '19010103': 17, '19010104': 18, '19010105': 19,
            '190102':20, '19010201': 21, '19010202': 22, '19010203': 23, '19010204': 24,
            '19010205': 25, '190103': 26, '19010301': 27, '19010302': 28, '19010399': 29,
            '19020101': 32, '19020102': 33, '19020103': 34, '19020104': 35, '19020105': 36,
            '19020201': 38, '19020202': 39, '19020203': 40, '19020204': 41, '19020205': 42,
            '190203': 43, '19020301': 44, '19020302': 45, '19020399': 46,
            '20': 47, '21': 48, '22': 48, '23': 49, '24': 50, '25': 51
        }

        sheet = wb.worksheets[21]  

        for row in podatoci: 
            vid_stavka = row[0]
            if vid_stavka in vid_stavka_mapping:
                target_row = vid_stavka_mapping[vid_stavka]
                start_column = 3  # Start writing from column C

                for col_offset, value in enumerate(row[1:]):  # Skip vid_stavka (index 0)
                    cell_column = start_column + col_offset
                    cell_row = target_row

                    # Skip specific rows or row-column pairs
                    if cell_row in rows_to_skip or (cell_row, cell_column) in row_column_to_skip:
                        continue

                    # Write value if not None
                    if value is not None:
                        sheet.cell(row=cell_row, column=cell_column, value=value)
            
        #-----#SP-4------------------- 
         #SP-5
        sql = (
        "SELECT vid_stavka, kol100,kol101,kol101a,kol102,kol103, kol104 ,"
         " kol105, kol106, kol107,kol200 "
        "FROM stat_izvestai "
        "WHERE stat_izvestaj = 'SP-5' and vid_stavka not in('Vkupno(01)','Vkupno (02)')   AND datum = LAST_DAY(mdy({},1,{}) ) order by stat_izvestaiid".format(mesec, godina) 
        )


        print(sql)
        results, OK = Connection.OSISinit()
        if not OK:
            return False, "Greska - nema vrska so baza za Sp-5"

        results.execute(sql)

        podatoci = []
        while True:
            row = results.fetchone()
            if not row:
                break
            podatoci.append(row)
        rows_to_skip = {26}
        row_column_to_skip = {}

        
        sheet = wb.worksheets[23]  
        target_row=12
        for row in podatoci: 
            vid_stavka = row[0]
            target_row = target_row+1
            if target_row==26:
                target_row = target_row+1
            start_column = 3  # Start writing from column C

            for col_offset, value in enumerate(row[1:]):  # Skip vid_stavka (index 0)
                cell_column = start_column + col_offset
                cell_row = target_row

                # Skip specific rows or row-column pairs
                if cell_row in rows_to_skip or (cell_row, cell_column) in row_column_to_skip:
                    continue

                # Write value if not None
                if value is not None:
                    sheet.cell(row=cell_row, column=cell_column, value=value)
            
        #-----#SP-5-------------------
                #SP-7
        sql = (
        "SELECT vid_stavka, kol100,kol101,kol102, kol103,kol104 ,"
         " kol105, kol106, kol107 "
        "FROM stat_izvestai "
        "WHERE stat_izvestaj = 'SP-7'   AND datum = LAST_DAY(mdy({},1,{}))".format(mesec, godina) 
        )


        print(sql)
        results, OK = Connection.OSISinit()
        if not OK:
            return False, "Greska - nema vrska so baza za Sp-7"

        results.execute(sql)

        podatoci = []
        while True:
            row = results.fetchone()
            if not row:
                break
            podatoci.append(row)
        rows_to_skip = {}
        row_column_to_skip = {}

        # Mapping vid_stavka to specific rows
        vid_stavka_mapping = {
            '19': 12, '1901': 13, '1902': 14,
            '20': 15, '21': 16, '22': 17, '23': 18, '24': 19, '25': 20,'100':21        }

        sheet = wb.worksheets[25]  

        for row in podatoci: 
            vid_stavka = row[0]
            if vid_stavka in vid_stavka_mapping:
                target_row = vid_stavka_mapping[vid_stavka]
                start_column = 3  # Start writing from column C

                for col_offset, value in enumerate(row[1:]):  # Skip vid_stavka (index 0)
                    cell_column = start_column + col_offset
                    cell_row = target_row

                    # Skip specific rows or row-column pairs
                    if cell_row in rows_to_skip or (cell_row, cell_column) in row_column_to_skip:
                        continue

                    # Write value if not None
                    if value is not None:
                        sheet.cell(row=cell_row, column=cell_column, value=value)
            
        #-----#SP-7------------------- 
        
        
               #SP-6
        sql = (
        "SELECT vid_stavka,client_name, kol101,kol102, kol103 "
        "FROM stat_izvestai "
        "WHERE stat_izvestaj = 'SP-6'   AND datum = LAST_DAY(mdy({},1,{})) order by stat_izvestaiid".format(mesec, godina) 
        )


        print(sql)
        results, OK = Connection.OSISinit()
        if not OK:
            return False, "Greska - nema vrska so baza za Sp-6"

        results.execute(sql)

        podatoci = []
        while True:
            row = results.fetchone()
            if not row:
                break
            podatoci.append(row)
        rows_to_skip = {16}
        row_column_to_skip = {(12,6),(13,6),(14,6),(15,6)}
        vid_stavka_start_row = { '100(1)', '100(2)', '100(3)', '100(99)'  }

        # Mapping vid_stavka to specific rows
        vid_stavka_mapping = {
            '100(1)': 12, '100(2)': 13, '100(3)': 14,
            '100(99)': 15, '200_1': 17, '200_2': 18, '200_3': 19       }

        sheet = wb.worksheets[24]  # Target worksheet

        current_row = 20  # Start inserting rows dynamically from row 20

        for row in podatoci:
            vid_stavka = row[0]
            target_row = vid_stavka_mapping.get(vid_stavka, None)  # Default to None if not in mapping
            start_column = 3
            k = 1

            # Adjust start column for specific vid_stavka
            if vid_stavka in vid_stavka_start_row:
                start_column = 4  # Start writing from column D
                k = 2

            # Handle vid_stavka starting with "200" or "300" dynamically
            if vid_stavka.startswith("200") and vid_stavka not in ["200", "200_1", "200_2", "200_3"]:
                target_row = current_row  # Use dynamic row
                sheet.insert_rows(target_row)
                print(f"Inserted a new row at {target_row} for vid_stavka {vid_stavka}")
                copy_formatting(19, target_row, sheet)
                print(f"Applied formatting from row 19 to row {target_row}")
                current_row += 1  # Move to the next row
                k=0
                start_column = 2
                formula_cell = sheet.cell(row=16, column=4)  # Adjust as needed
                print(formula_cell)
                formula = f"=SUM(D17:D{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=16, column=5)  # Adjust as needed
                formula = f"=SUM(E17:E{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=16, column=6)  # Adjust as needed
                formula = f"=SUM(F17:F{current_row})"
                formula_cell.value = formula

            if vid_stavka.startswith("300") and vid_stavka  in ["300", "300_1", "300_2", "300_3"]:
                target_row = current_row  # Use dynamic row
                print(f"notInserted a new row at {target_row} for vid_stavka {vid_stavka}")
                current_row += 1  # Move to the next row 

                if  vid_stavka  in ["300"]:
                    start_row300=current_row
                    print(f"start_row300 {start_row300}")
                    current_row += 1 
                    target_row = current_row
                    start_row=current_row                    

            if vid_stavka.startswith("300") and vid_stavka not in ["300", "300_1", "300_2", "300_3"]:
                target_row = current_row  # Use dynamic row
                sheet.insert_rows(target_row)
                print(f"Inserted a new row at {target_row} for vid_stavka {vid_stavka}")
                copy_formatting(19, target_row, sheet)
                print(f"Applied formatting from row 19 to row {target_row}")
                current_row += 1  # Move to the next row
                k=0
                start_column = 2
            if vid_stavka.startswith("400(1)") or vid_stavka.startswith("400(2)") or vid_stavka.startswith("400(3)") or vid_stavka.startswith("400(99)"):
                target_row = current_row  # Use dynamic row
                print(f"notInserted a new row at {target_row} for vid_stavka {vid_stavka}")
                current_row += 1  # Move to the next row 
                target_row = current_row
                start_row=target_row+1
                if  vid_stavka  in ["400(1)","400(2)","400(3)","400(99)"]:
                    if vid_stavka=="400(1)":
                        start_row4001=target_row
                    if vid_stavka=="400(2)":
                        current_row += 1  # Move to the next row 
                        target_row = current_row
                        start_row=target_row+1
                        start_row4002=target_row
                        print(f"start_row4002 {start_row4002}")
                    if vid_stavka=="400(3)":
                        current_row += 1  # Move to the next row 
                        target_row = current_row
                        start_row=target_row+1
                        start_row4003=target_row
                        print(f"start_row4003 {start_row4003}")
                    if vid_stavka=="400(99)":
                        current_row += 1  # Move to the next row 
                        target_row = current_row
                        start_row=target_row+1
                        start_row4009=target_row
                        print(f"start_row4009 {start_row4009}")

                    print(f"start_row4001 {start_row4001}")
                    
                    
                    
                if vid_stavka.startswith("400(1)"):       
                    formula_cell = sheet.cell(row=start_row4001, column=4)  # Adjust as needed
                    formula = f"=SUM(D{start_row4001+1}:D{current_row-1})"
                    formula_cell.value = formula
                    formula_cell = sheet.cell(row=start_row4001, column=5)  # Adjust as needed
                    formula = f"=SUM(E{start_row4001+1}:E{current_row-1})"
                    formula_cell.value = formula
                    formula_cell = sheet.cell(row=start_row4001, column=6)  # Adjust as needed
                    formula = f"=SUM(F{start_row4001+1}:F{current_row-1})"
                    formula_cell.value = formula
                if vid_stavka.startswith("400(2)"):       
                    formula_cell = sheet.cell(row=start_row4002, column=4)  # Adjust as needed
                    formula = f"=SUM(D{start_row4002+1}:D{current_row-1})"
                    formula_cell.value = formula
                    formula_cell = sheet.cell(row=start_row4002, column=5)  # Adjust as needed
                    formula = f"=SUM(E{start_row4002+1}:E{current_row-1})"
                    formula_cell.value = formula
                    formula_cell = sheet.cell(row=start_row4002, column=6)  # Adjust as needed
                    formula = f"=SUM(F{start_row4002+1}:F{current_row-1})"
                    formula_cell.value = formula
                if vid_stavka.startswith("400(3)"):       
                    formula_cell = sheet.cell(row=start_row4003, column=4)  # Adjust as needed
                    formula = f"=SUM(D{start_row4003+1}:D{current_row-1})"
                    formula_cell.value = formula
                    formula_cell = sheet.cell(row=start_row4003, column=5)  # Adjust as needed
                    formula = f"=SUM(E{start_row4003+1}:E{current_row-1})"
                    formula_cell.value = formula
                    formula_cell = sheet.cell(row=start_row4003, column=6)  # Adjust as needed
                    formula = f"=SUM(F{start_row4003+1}:F{current_row-1})"
                    formula_cell.value = formula
                if vid_stavka.startswith("400(99)"):       
                    formula_cell = sheet.cell(row=start_row4009, column=4)  # Adjust as needed
                    formula = f"=SUM(D{start_row4009+1}:D{current_row-1})"
                    formula_cell.value = formula
                    formula_cell = sheet.cell(row=start_row4009, column=5)  # Adjust as needed
                    formula = f"=SUM(E{start_row4009+1}:E{current_row-1})"
                    formula_cell.value = formula
                    formula_cell = sheet.cell(row=start_row4009, column=6)  # Adjust as needed
                    formula = f"=SUM(F{start_row4009+1}:F{current_row-1})"
                    formula_cell.value = formula                    
                

            if vid_stavka.startswith("9999") :
                target_row = current_row  # Use dynamic row
                print(f"notInserted a new row at {target_row} for vid_stavka {vid_stavka}")
                start_column = 4  # Start writing from column D
                k = 2
                current_row += 1  # Move to the next row 
                
                if  vid_stavka  in ["9999"]:
                    current_row += 1 
                    target_row = current_row 
                    start_row=current_row
                    start_row9999=current_row
                formula_cell = sheet.cell(row=start_row9999, column=4)  # Adjust as needed
                formula = f"=SUM(D{start_row9999+1}:D{current_row-1})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=start_row9999, column=5)  # Adjust as needed
                formula = f"=SUM(E{start_row9999+1}:E{current_row-1})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=start_row9999, column=6)  # Adjust as needed
                formula = f"=SUM(F{start_row9999+1}:F{current_row-1})"
                
            if vid_stavka.startswith("0000") :
                current_row += 1 
                formula_cell = sheet.cell(row=current_row, column=4)  # Adjust as needed
                print (formula_cell)
                formula = f"=D11+D16+D{start_row300}+D{start_row4001}+D{start_row4002}+D{start_row4003}+D{start_row4009}+D{start_row9999}"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=current_row, column=5)  # Adjust as needed
                print (formula_cell)
                formula = f"=E11+E16+E{start_row300}+E{start_row4001}+E{start_row4002}+E{start_row4003}+E{start_row4009}+E{start_row9999}"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=current_row, column=6)  # Adjust as needed
                print (formula_cell)
                formula = f"=F11+F16+F{start_row300}+F{start_row4001}+F{start_row4002}+F{start_row4003}+F{start_row4009}+F{start_row9999}"
                formula_cell.value = formula
                

            # Write data to cells
            if target_row:  # If a row was mapped or inserted
                for col_offset, value in enumerate(row[k:]):  # Skip vid_stavka
                    cell_column = start_column + col_offset
                    cell_row = target_row

                    # Skip rows or row-column pairs as defined
                    if cell_row in rows_to_skip or (cell_row, cell_column) in row_column_to_skip:
                        continue

                    # Write value if not None
                    if value is not None:
                        sheet.cell(row=cell_row, column=cell_column, value=value)

            
        #-----#SP-6------------------- 
        #SP-8
        sql = (
        "SELECT vid_stavka,client_name, kol101,kol102, kol103,kol200,kol201 "
        "FROM stat_izvestai "
        "WHERE stat_izvestaj = 'SP-8'   AND datum = LAST_DAY(mdy({},1,{})) order by stat_izvestaiid".format(mesec, godina) 
        )


        print(sql)
        results, OK = Connection.OSISinit()
        if not OK:
            return False, "Greska - nema vrska so baza za Sp-8"

        results.execute(sql)

        podatoci = []
        while True:
            row = results.fetchone()
            if not row:
                break
            podatoci.append(row)
        rows_to_skip = {12}
        row_column_to_skip = {}
        vid_stavka_start_row = { '100'  }

        # Mapping vid_stavka to specific rows
        vid_stavka_mapping = {
            '100': 11,  '200_1': 13, '200_2': 14, '200_3': 15       }

        sheet = wb.worksheets[26]  # Target worksheet

        current_row = 16  # Start inserting rows dynamically from row 20

        for row in podatoci:
            vid_stavka = row[0]
            target_row = vid_stavka_mapping.get(vid_stavka, None)  # Default to None if not in mapping
            start_column = 3
            k = 1

            # Adjust start column for specific vid_stavka
            if vid_stavka in vid_stavka_start_row:
                start_column = 4  # Start writing from column D
                k = 2

            # Handle vid_stavka starting with "200" or "300" dynamically
            if vid_stavka.startswith("200") and vid_stavka not in ["200", "200_1", "200_2", "200_3"]:
                target_row = current_row  # Use dynamic row
                sheet.insert_rows(target_row)
                #print(f"Inserted a new row at {target_row} for vid_stavka {vid_stavka}")
                copy_formatting(13, target_row, sheet)
                #print(f"Applied formatting from row 19 to row {target_row}")
                current_row += 1  # Move to the next row
                k=0
                start_column = 2
                formula_cell = sheet.cell(row=12, column=4)  # Adjust as needed
                formula = f"=SUM(D13:D{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=12, column=5)  # Adjust as needed
                formula = f"=SUM(E13:E{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=12, column=6)  # Adjust as needed
                formula = f"=SUM(F13:F{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=12, column=7)  # Adjust as needed
                formula = f"=SUM(G13:G{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=12, column=8)  # Adjust as needed
                formula = f"=SUM(H13:H{current_row})"
                formula_cell.value = formula


            if vid_stavka.startswith("300") and vid_stavka  in ["300", "300_1", "300_2", "300_3"]:
                target_row = current_row  # Use dynamic row
                #print(f"notInserted a new row at {target_row} for vid_stavka {vid_stavka}")
                current_row += 1  # Move to the next row 

                if  vid_stavka  in ["300"]:
                    start_row300=current_row
                    print(start_row300);
                    current_row += 1 
                    target_row = current_row
                    start_row=current_row 
                   
                #print(vid_stavka)
                #print('aaaa')
                #print(start_row)
                #print(current_row)
                formula_cell = sheet.cell(row=start_row300, column=4)  # Adjust as needed
                formula = f"=SUM(D{start_row300+1}:D{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=start_row300, column=5)  # Adjust as needed
                formula = f"=SUM(E{start_row300+1}:E{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=start_row300, column=6)  # Adjust as needed
                formula = f"=SUM(F{start_row300+1}:F{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=start_row300, column=7)  # Adjust as needed
                formula = f"=SUM(G{start_row300+1}:G{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=start_row300, column=8)  # Adjust as needed
                formula = f"=SUM(H{start_row300+1}:H{current_row})"
                formula_cell.value = formula

           
                
            if vid_stavka.startswith("400") and vid_stavka  in ["400", "400(1)_1"]:
                target_row = current_row  # Use dynamic row
                print(f"notInserted a new row at {target_row} for vid_stavka {vid_stavka}")
                current_row += 1  # Move to the next row 
                
                if  vid_stavka  in ["400"]:
                    target_row = current_row
                    start_row=current_row 
                    start_row400=current_row
                    continue                    
                if  vid_stavka  in ["400(1)_1"]: 
                    target_row = current_row                   
                
                formula_cell = sheet.cell(row=start_row400, column=4)  # Adjust as needed
                formula = f"=SUM(D{start_row400+1}:D{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=start_row400, column=5)  # Adjust as needed
                formula = f"=SUM(E{start_row400+1}:E{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=start_row400, column=6)  # Adjust as needed
                formula = f"=SUM(F{start_row400+1}:F{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=start_row400, column=7)  # Adjust as needed
                formula = f"=SUM(G{start_row400+1}:G{current_row})"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=start_row400, column=8)  # Adjust as needed
                formula = f"=SUM(H{start_row400+1}:H{current_row})"
                formula_cell.value = formula
                

            if vid_stavka.startswith("9999") :
                current_row += 4
                start_row9999=current_row
                target_row = current_row  # Use dynamic row
                start_column = 4  # Start writing from column D
                k = 2
                current_row += 1  # Move to the next row 
            if vid_stavka.startswith("0000") :
                formula_cell = sheet.cell(row=current_row, column=4)  # Adjust as needed
                formula = f"=D11+D12+D{start_row300}+D{start_row400}+D{start_row9999}"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=current_row, column=5)  # Adjust as needed
                print (formula_cell)
                formula = f"=E11+E12+E{start_row300}+E{start_row400}+E{start_row9999}"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=current_row, column=6)  # Adjust as needed
                print (formula_cell)
                formula = f"=F11+F12+F{start_row300}+F{start_row400}+F{start_row9999}"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=current_row, column=7)  # Adjust as needed
                print (formula_cell)
                formula = f"=G11+G12+G{start_row300}+G{start_row400}+G{start_row9999}"
                formula_cell.value = formula
                formula_cell = sheet.cell(row=current_row, column=8)  # Adjust as needed
                print (formula_cell)
                formula = f"=H11+H12+H{start_row300}+H{start_row400}+H{start_row9999}"
                formula_cell.value = formula
            # Write data to cells
            if target_row:  # If a row was mapped or inserted
                for col_offset, value in enumerate(row[k:]):  # Skip vid_stavka
                    cell_column = start_column + col_offset
                    cell_row = target_row

                    # Skip rows or row-column pairs as defined
                    if cell_row in rows_to_skip or (cell_row, cell_column) in row_column_to_skip:
                        continue

                    # Write value if not None
                    if value is not None:
                        sheet.cell(row=cell_row, column=cell_column, value=value)

            
        #-----#SP-6------------------- 
        # Save the workbook
        wb.save(fileOUT)
    except Exception as e:
        greska = f"GRESKA: Ne mozhe da se zapise vo {fileOUT}: {str(e)}"
        return False, greska
    try:
        if platform.system() == "Windows":
            os.startfile(fileOUT)
        elif platform.system() == "Darwin":  # macOS
            subprocess.call(["open", fileOUT])
        else:  # Linux
            subprocess.call(["xdg-open", fileOUT])
    except Exception as e:
        print(f"Could not open the Excel file: {str(e)}")
    return OK, 'ok e'
    
def copy_formatting(source_row, target_row, sheet):
    # Iterate over each column in the source row to copy its formatting
    for col in range(1, sheet.max_column + 1):
        source_cell = sheet.cell(row=source_row, column=col)
        target_cell = sheet.cell(row=target_row, column=col)
        
        # Explicitly copy font, fill, alignment, and border properties
        target_cell.font = source_cell.font.copy() if source_cell.font else None
        target_cell.fill = source_cell.fill.copy() if source_cell.fill else None
        target_cell.alignment = source_cell.alignment.copy() if source_cell.alignment else None
        target_cell.border = copy_borders(source_cell.border) if source_cell.border else None

# Function to copy borders from one cell to another
def copy_borders(source_border):
    # Copy each side of the border
    top = source_border.top
    left = source_border.left
    right = source_border.right
    bottom = source_border.bottom
     # Return a new Border object with the same properties
    return Border(top=top, left=left, right=right, bottom=bottom)
    
import pandas as pd
from openpyxl import Workbook

# Define function to fetch data using your method
def fetch_data_from_db(sql):
    print(sql)
    results, OK = Connection.OSISinit()  # Initialize the connection
    if not OK:
        print("Greska - nema vrska so baza")
        return None, "Greska - nema vrska so baza"

    # Execute SQL query
    results.execute(sql)
    podatoci = []
    
    # Fetch data row by row
    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)

    results.close()
    return podatoci, None

def SP1analitika2(mesec, godina):
    query1 = """
    SELECT vrati_grupa(d.os_ponuda_detailid) grupa_sp1,
           polisa_broj_cel,
           SUM(NVL(br_osig_aktivni, 1)) br_osigurenici,
           SUM(CASE 
                   WHEN vrati_tipprodukt(p.os_tipproduktid) IN ('КР', 'КЖ') THEN NVL(br_osig_aktivni, 1) 
                   ELSE 0 
               END) br_osigurenici_kolekt,
           SUM(CASE 
                   WHEN NVL(o.par_valutaid, p.par_valutaid) = 363 THEN NVL(osig_suma_smrt, osig_suma) 
                   ELSE NVL(osig_suma_smrt, osig_suma) * 61.5 
               END) osig_suma
    FROM os_ponuda o, os_ponuda_detail d, os_produkt p, os_polisa t
    WHERE o.os_ponudaid = d.os_ponudaid
      AND o.os_produktid = p.os_produktid
      AND o.os_ponudaid = t.os_ponudaid
      AND skadenca_datum_od <= LAST_DAY(mdy({},1,{}))
      AND skadenca_datum_do >= LAST_DAY(mdy({},1,{}))
      AND o.par_statusid IN (17, 18, 13, 42)
      AND ponuda_podbroj = maxpodbroj_datum(o.ponuda_broj, t.polisa_broj, o.os_produktid, LAST_DAY(mdy({},1,{})))
    GROUP BY 1, 2      """.format(mesec, godina,mesec, godina,mesec, godina) 

    query2 = """
    SELECT vrati_grupa(d.os_ponuda_detailid) grupa_sp1,
           polisa_broj_cel
    FROM os_ponuda o, os_ponuda_detail d, os_polisa t
    WHERE o.os_ponudaid = d.os_ponudaid
      AND o.os_ponudaid = t.os_ponudaid
      AND skadenca_datum_od <= LAST_DAY(mdy({},1,{}))
      AND skadenca_datum_do >= LAST_DAY(mdy({},1,{}))
      AND o.par_statusid IN (18)
      AND ponuda_podbroj = maxpodbroj_datum(o.ponuda_broj, t.polisa_broj, o.os_produktid,LAST_DAY(mdy({},1,{})))
    """.format(mesec, godina,mesec, godina,mesec, godina) 

    # Fetch data for both queries
    data1, error1 = fetch_data_from_db(query1)
    data2, error2 = fetch_data_from_db(query2)

    if error1 or error2:
        print("Error fetching data")
        return OK,"Error fetching data"
        exit()

    # Convert data to DataFrames
    columns1 = ['grupa_sp1', 'polisa_broj', 'br_osigurenici', 'br_osigurenici_kolekt', 'osig_suma']
    columns2 = ['grupa_sp1', 'polisa_broj']
    df1 = pd.DataFrame(data1, columns=columns1)
    df2 = pd.DataFrame(data2, columns=columns2)

    # Write data to Excel with multiple sheets
    mu1 = "SP1_analitika.xlsx"
    configDIR, inputDIR, sep = Directories(str(mesec), str(godina))
    print(mu1, configDIR, inputDIR)
    mustra1 = os.path.join(configDIR, mu1)    
    print(mustra1)
    print(inputDIR)
    if not os.path.exists(inputDIR):
            os.makedirs(inputDIR)
    if os.path.exists(mustra1):
        try:
            os.remove(mustra1)
        except PermissionError:
            print(f"Не могу удалить {mustra1}, файл занят!")
            raise

    with pd.ExcelWriter(mustra1, engine='openpyxl') as writer:
        df1.to_excel(writer, sheet_name="Skluceni polisi", index=False)
        df2.to_excel(writer, sheet_name="Kapitailizirani polisi", index=False)

    print(f"Data exported to {mustra1}")
    
    try:
        if platform.system() == "Windows":
            os.startfile(mustra1)
        elif platform.system() == "Darwin":  # macOS
            subprocess.call(["open", fileOUT])
        else:  # Linux
            subprocess.call(["xdg-open", mustra1])
    except Exception as e:
        print(f"Could not open the Excel file: {str(e)}")
    return OK,f"Data exported to {mustra1}"

# Function to execute SQL queries and fetch results
def fetch_query_results(sql):
    print (sql);
    results, OK = Connection.OSISinit()
    if not OK:
        print("Error: Unable to connect to the database.")
        return None
    
    # Execute the SQL query
    results.execute(sql)
    columns = [col[0] for col in results.description]  # Fetch column names
    rows = results.fetchall()  # Fetch all data
    results.close()
    return pd.DataFrame(rows, columns=columns)  # Convert to DataFrame
    


def SP1analitika2(mesec, godina):
    queries = {
        "steti": f"""
            SELECT vrati_grupa(d.os_ponuda_detailid) grupa_sp1,
                   polisa_broj_cel,
                   SUM(NVL(br_osig_aktivni, 1)) br_osigurenici,
                   SUM(CASE 
                           WHEN vrati_tipprodukt(p.os_tipproduktid) IN ('КР', 'КЖ') THEN NVL(br_osig_aktivni, 1) 
                           ELSE 0 
                       END) br_osigurenici_kolekt,
                   SUM(CASE 
                           WHEN NVL(o.par_valutaid, p.par_valutaid) = 363 THEN NVL(osig_suma_smrt, osig_suma) 
                           ELSE NVL(osig_suma_smrt, osig_suma) * 61.5 
                       END) osig_suma
            FROM os_ponuda o, os_ponuda_detail d, os_produkt p, os_polisa t
            WHERE o.os_ponudaid = d.os_ponudaid
              AND o.os_produktid = p.os_produktid
              AND o.os_ponudaid = t.os_ponudaid
              AND skadenca_datum_od <= LAST_DAY(mdy({mesec}, 1, {godina}))
              AND skadenca_datum_do >= LAST_DAY(mdy({mesec}, 1, {godina}))
              AND o.par_statusid IN (17, 18, 13, 42)
              AND ponuda_podbroj = maxpodbroj_datum(o.ponuda_broj, t.polisa_broj, o.os_produktid, LAST_DAY(mdy({mesec}, 1, {godina})))
            GROUP BY 1, 2;
        """,

        "kapitalizirani_polisi": f"""
            SELECT vrati_grupa(d.os_ponuda_detailid) grupa_sp1, polisa_broj_cel
            FROM os_ponuda o, os_ponuda_detail d, os_polisa t
            WHERE o.os_ponudaid = d.os_ponudaid
              AND o.os_ponudaid = t.os_ponudaid
              AND skadenca_datum_od <= LAST_DAY(mdy({mesec}, 1, {godina}))
              AND skadenca_datum_do >= LAST_DAY(mdy({mesec}, 1, {godina}))
              AND o.par_statusid IN (18)
              AND ponuda_podbroj = maxpodbroj_datum(o.ponuda_broj, t.polisa_broj, o.os_produktid, LAST_DAY(mdy({mesec}, 1, {godina})));
        """,

        "otkup": f"""
            SELECT vrati_grupa(d.os_ponuda_detailid) grupa_sp1, polisa_broj_cel
            FROM os_ponuda o, os_ponuda_detail d, os_polisa t
            WHERE o.os_ponudaid = d.os_ponudaid
              AND o.os_ponudaid = t.os_ponudaid
              AND skadenca_datum_od <= LAST_DAY(mdy({mesec}, 1, {godina}))
              AND skadenca_datum_do >= LAST_DAY(mdy({mesec}, 1, {godina}))
              AND o.par_statusid IN (20, 21)
              AND ponuda_podbroj = maxpodbroj_datum(o.ponuda_broj, t.polisa_broj, o.os_produktid, LAST_DAY(mdy({mesec}, 1, {godina})));
        """,

        "skluceni_dogovori": f"""
            SELECT vrati_grupa(d.os_ponuda_detailid) grupa_sp1, polisa_broj_cel
            FROM os_ponuda o, os_ponuda_detail d, os_polisa p
            WHERE o.os_ponudaid = d.os_ponudaid
              AND o.os_ponudaid = p.os_ponudaid
              AND p.datum_polisa BETWEEN '01.01.{godina}' AND LAST_DAY(mdy({mesec}, 1, {godina}))
              AND o.par_statusid IN (17, 18)
              AND ponuda_podbroj = maxpodbroj_datum(o.ponuda_broj, p.polisa_broj, o.os_produktid, LAST_DAY(mdy({mesec}, 1, {godina})));
        """,

        "bruto_premija": f"""
            SELECT sap_risk_business[3,10] grupa_sp1, dokument[1,10] polisa_broj, SUM(NVL(iznos_p, 0)) bruto_premija
            FROM stavka
            WHERE dat_nalog BETWEEN '01.01.{godina}' AND LAST_DAY(mdy({mesec}, 1, {godina}))
              AND konto[1,3] = '700'
            GROUP BY 1, 2;
        """,

        "bruto_premija_12": f"""
            SELECT sap_risk_business[3,10] grupa_sp1, dokument[1,10] polisa_broj, SUM(NVL(iznos_p, 0)) bruto_premija_12
            FROM stavka
            WHERE dat_nalog BETWEEN LAST_DAY(mdy({mesec}, 1, {int(godina)-1})) AND LAST_DAY(mdy({mesec}, 1, {godina}))
              AND konto[1,3] = '700'
              AND sap_risk_business IS NOT NULL
            GROUP BY 1, 2;
        """,

        "edinecna_premija": f"""
            SELECT sap_risk_business[3,10] grupa_sp1, dokument[1,10] polisa_broj, SUM(NVL(iznos_p, 0)) edinecna_premija
            FROM stavka s, os_polisa p, os_ponuda po, os_produkt pr
            WHERE s.dokument[1,10] = p.polisa_broj_cel
              AND s.dokument[11,14] = p.polisa_pod_broj
              AND p.os_ponudaid = po.os_ponudaid
              AND po.os_produktid = pr.os_produktid
              AND vrati_tipprodukt(pr.os_tipproduktid) NOT IN ('КР', 'КЖ')
              AND s.dat_nalog BETWEEN '01.01.{godina}' AND LAST_DAY(mdy({mesec}, 1, {godina}))
              AND konto[1,3] = '700'
              AND sap_risk_business IS NOT NULL
            GROUP BY 1, 2;
        """
    }
    # Initialize an Excel writer
    mu1 = "SP1_analitika.xlsx"
    configDIR, inputDIR, sep = Directories(str(mesec), str(godina))
    print(mu1, configDIR, inputDIR)
    mustra1 = os.path.join(inputDIR, mu1)
    print(mustra1)
    print (inputDIR)
    if not os.path.exists(inputDIR):
            os.makedirs(inputDIR)
    if os.path.exists(mustra1):
        try:
            os.remove(mustra1)
        except PermissionError:
            print(f"Не могу удалить {mustra1}, файл занят!")
            raise

    with pd.ExcelWriter(mustra1, engine='openpyxl') as writer:
        for sheet_name, sql in queries.items():
            print(f"Fetching data for {sheet_name}...")
            df = fetch_query_results(sql)
            if df is not None:
                print(f"Writing {sheet_name} to Excel...")
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Data exported to {mustra1}")
    
    try:
        if platform.system() == "Windows":
            os.startfile(mustra1)
        elif platform.system() == "Darwin":  # macOS
            subprocess.call(["open", fileOUT])
        else:  # Linux
            subprocess.call(["xdg-open", mustra1])
    except Exception as e:
        print(f"Could not open the Excel file: {str(e)}")
    return OK,f"Data exported to {mustra1}"
   

def SP2analitika(mesec, godina):
    queries = {
        "steti": f"""
            select sap_risk_biznis[3,10],steta_broj||'/'||steta_godina  prij_neiz, '' prij_izv,'' odb, ''  isp, ''  otk, '' rezr_izv , '' rezr_neiz,0  isp_iznos,0  otk_iznos
            from sostojba_steta
            where steta_datum_prijava between '01.01.{godina}' and LAST_DAY(mdy({mesec}, 1, {godina}))  
            and par_tip_stetaid<>4

            union 
            select vrati_grupa(d.os_ponuda_detailid ) grupa_sp1, '' prij_neiz,   t.polisa_broj_cel prij_izv,'' odb, '' isp, ''  otk, '' rezr_izv , '' rezr_neiz,0  isp_iznos,0  otk_iznos
            from os_ponuda o, os_ponuda_detail d, os_produkt p, os_polisa t
            where o.os_ponudaid=d.os_ponudaid 
            and o.os_produktid=p.os_produktid
            and o.os_ponudaid=t.os_ponudaid 
            and skadenca_datum_do between '01.01.{godina}' and LAST_DAY(mdy({mesec}, 1, {godina})) 
            and o.par_statusid in  ( 36,37,38,42) 
            and ponuda_podbroj=maxpodbroj_datum(o.ponuda_broj , t.polisa_broj, o.os_produktid, LAST_DAY(mdy({mesec}, 1, {godina}))  )

            union

            select sap_risk_biznis[3,10], '' prij_neiz, '' prij_izv, steta_broj||'/'||steta_godina  odb, '' isp, ''  otk , '' rezr_izv , ''rezr_neiz,0  isp_iznos,0  otk_iznos
            from sostojba_steta 
            where 1 = 1 and likv_datum >='01.01.{godina}'  and likv_datum <=LAST_DAY(mdy({mesec}, 1, {godina})) 
            and vratilikizn_steta(l_stetaid,'01.01.2005',LAST_DAY(mdy({mesec}, 1, {godina})))= 0 
            and par_tip_stetaid<>4
             
            union 

            select sap_risk_biznis[3,10], '' prij_neiz, '' prij_izv,  ''  odb, ''  isp, ''  otk , steta_broj||'/'||steta_godina rezr_izv , '' rezr_neiz,
            0  isp_iznos,0  otk_iznos
            from sostojba_steta 
            where 1 = 1  
            and vratirezizn_steta(l_stetaid,'01.01.2005',LAST_DAY(mdy({mesec}, 1, {godina})))!= 0 
            and par_tip_stetaid<>4


            union
            select sap_risk_biznis[3,10], '' prij_neiz, '' prij_izv,'' odb, case when  par_tip_stetaid<>4 then   steta_broj||'/'||steta_godina else '' end  isp,  
            case when  par_tip_stetaid=4 then  steta_broj||'/'||steta_godina else '' end   otk  , '' rezr_izv ,'' rezr_neiz,  sum(case when  par_tip_stetaid<>4 
            then  vratilikizn_steta_den(l_stetaid,'01.01.{godina}',LAST_DAY(mdy({mesec}, 1, {godina}))) else 0 end )  isp_iznos,  
            sum(case when  par_tip_stetaid=4 then  vratilikizn_steta_den(l_stetaid,'01.01.{godina}',LAST_DAY(mdy({mesec}, 1, {godina}))) else 0 end )  otk_iznos 
            from sostojba_steta 
            where 1 = 1 and likv_datum >='01.01.{godina}'  and likv_datum <=LAST_DAY(mdy({mesec}, 1, {godina})) 
            and vratilikizn_steta(l_stetaid,'01.01.{godina}',LAST_DAY(mdy({mesec}, 1, {godina})))!= 0
            group by 1,5,6


        """
    }
    # Initialize an Excel writer
    mu1 = "SP2_analitika.xlsx"
    configDIR, inputDIR, sep = Directories(str(mesec), str(godina))
    print(mu1, configDIR, inputDIR)
    mustra1 = os.path.join(inputDIR, mu1)
    print(mustra1)

    with pd.ExcelWriter(mustra1, engine='openpyxl') as writer:
        for sheet_name, sql in queries.items():
            print(f"Fetching data for {sheet_name}...")
            df = fetch_query_results(sql)
            if df is not None:
                print(f"Writing {sheet_name} to Excel...")
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Data exported to {mustra1}")
    
    try:
        if platform.system() == "Windows":
            os.startfile(mustra1)
        elif platform.system() == "Darwin":  # macOS
            subprocess.call(["open", fileOUT])
        else:  # Linux
            subprocess.call(["xdg-open", mustra1])
    except Exception as e:
        print(f"Could not open the Excel file: {str(e)}")
    return OK,f"Data exported to {mustra1}"
   




















    