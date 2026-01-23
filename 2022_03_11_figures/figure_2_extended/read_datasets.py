import pandas as pd
import utils

### READ ALL INPUT DATASETS

# Read all splice site statistics, including the runs of GC1 and 15P1 from June 12, the run from June 26 (where mESC was very low on RNA molecules, but GC-1 and 15P-1 were good), and July 16 with HEK and HeLa where all samples seem good (especially HEK)
NUM_LIBS = 14
ALL_LIBRARY_NAMES = { 
    0: "ES7A1p_GC1_old", 
    1: "ES7A5p_GC1_old", 
    2: "ES7A1p_15P1_old", 
    3: "ES7A5p_15P1_old",
    4: "ES7A5p_mESC_2e6", 
    5: "ES7A5p_mESC_5e6", 
    6: "ES7A1p_GC1", 
    7: "ES7A1p_15P1", 
    8: "ES7A_HEK293T_60mm",
    9: "ES7A_HEK293T_uncompress",
    10:"ES7A_HeLa_compress",
    11:"ES7_HeLa_A",
    12:"ES7_HeLa_B",
    13:"ES7_HeLa_C",
}
ALL_FILE_NAMES = { 
    0: "BS06906A_S17" , 
    1: "BS06907A_S18" , 
    2: "BS06908A_S19"  , 
    3: "BS06909A_S20", 
    4: "BS07024A_S1", 
    5: "BS07025A_S2", 
    6: "BS07026A_S3" , 
    7: "BS07027A_S4", 
    8: "BS07315A_S1",
    9: "BS07316A_S2",
    10:"BS07317A_S3",
    11: "BS11504A_S1",
    12: "BS11505A_S2",
    13: "BS11506A_S3",
}

DATA_FOLDER = "../splicing_library_analysis/data/ES7/"

def read_all_datasets(filter_cryptic_restriction_site = True, structure_file_name = 'all_exons_with_top_level_mfe.csv.zip', structure_fields = ["MFE", "structure"]):
    exons_mfe = pd.read_csv(DATA_FOLDER+structure_file_name).set_index("barcode")[structure_fields]

    all_barcode_statistics = []
    for lib_num in range(NUM_LIBS):
        FILE_NAME = ALL_FILE_NAMES[lib_num]
        FULL_FILE_NAME = DATA_FOLDER + FILE_NAME

        barcode_statistics = pd.read_csv(FULL_FILE_NAME+'_splicing_analysis.csv').set_index("barcode")
        barcode_statistics = barcode_statistics[barcode_statistics.badly_coupled == False] # remove badly coupled barcodes
        
        # Filter barcodes containing restriction site, as those contain artifacts
        if (filter_cryptic_restriction_site):
            contains_restriction_site = barcode_statistics.apply(lambda x: utils.contains_Esp3I_site(utils.add_flanking(x.exon,5)) or utils.contains_Esp3I_site(utils.add_barcode_flanking(x.name,5)), axis=1)
            barcode_statistics = barcode_statistics[~contains_restriction_site]
        
        barcode_statistics = barcode_statistics.merge(exons_mfe, on='barcode')

        barcode_statistics["others"] = barcode_statistics.num_unknown_splicing+barcode_statistics.num_intron_retention+barcode_statistics.num_bad_reads+barcode_statistics.num_bad_exon1
        barcode_statistics["total"] = barcode_statistics.others + barcode_statistics.num_exon_skipping + barcode_statistics.num_exon_inclusion +  barcode_statistics.num_splicing_in_exon

        ## Filter only plasmids with at least 20 total reads
        MIN_READS = 20
        barcode_statistics = barcode_statistics[barcode_statistics.num_exon_skipping +  barcode_statistics.num_exon_inclusion >= MIN_READS]

        # Also, we want inclusion and skipping to be at least 80% of the total reads; this gets rid of splice sites inside exon
        barcode_statistics = barcode_statistics[(barcode_statistics.num_exon_inclusion+barcode_statistics.num_exon_skipping)/barcode_statistics.total > 0.8]

        all_barcode_statistics.append(barcode_statistics)
        
    return all_barcode_statistics


def read_all_datasets_no_filtering():
    all_barcode_statistics = []
    for lib_num in range(NUM_LIBS):
        FILE_NAME = ALL_FILE_NAMES[lib_num]
        FULL_FILE_NAME = DATA_FOLDER + FILE_NAME

        barcode_statistics = pd.read_csv(FULL_FILE_NAME+'_splicing_analysis.csv').set_index("barcode")
        #barcode_statistics = barcode_statistics[barcode_statistics.badly_coupled == False] # remove badly coupled barcodes        
      
        #barcode_statistics["others"] = barcode_statistics.num_unknown_splicing+barcode_statistics.num_intron_retention+barcode_statistics.num_bad_reads+barcode_statistics.num_bad_exon1
        #barcode_statistics["total"] = barcode_statistics.others + barcode_statistics.num_exon_skipping + barcode_statistics.num_exon_inclusion +  barcode_statistics.num_splicing_in_exon

        all_barcode_statistics.append(barcode_statistics)
        
    return all_barcode_statistics