-- impc.`annotation extension` definition

CREATE TABLE `annotation extension` (
  `annotation_extension_id` int unsigned NOT NULL AUTO_INCREMENT,
  `annotation_extension_name` varchar(1000) DEFAULT NULL,
  PRIMARY KEY (`annotation_extension_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.cleanedData definition


CREATE TABLE `disease ontology term` (
  `do_term_id` char(12) NOT NULL,
  `do_term_name` text,
  PRIMARY KEY (`do_term_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`gene ontology term` definition

CREATE TABLE `gene ontology term` (
  `go_term_id` char(10) NOT NULL,
  `go_aspect` char(1) DEFAULT NULL,
  `go_term_name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`go_term_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`go annotation references` definition

CREATE TABLE `go annotation references` (
  `reference_id` int unsigned NOT NULL AUTO_INCREMENT,
  `reference_code` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`reference_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`group` definition

CREATE TABLE `group` (
  `group_name` varchar(100) DEFAULT NULL,
  `group_id` int unsigned NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`group_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`mouse gene` definition

CREATE TABLE `mouse gene` (
  `mouse_gene_accession_id` char(11) NOT NULL,
  `mouse_gene_symbol` char(13) DEFAULT NULL,
  PRIMARY KEY (`mouse_gene_accession_id`),
  UNIQUE KEY `unq_mouse gene` (`mouse_gene_accession_id`),
  CONSTRAINT `chk_mouse gene_symbol` CHECK ((char_length(`mouse_gene_symbol`) between 1 and 13)),
  CONSTRAINT `chk_mouse_gene_accession_id` CHECK ((char_length(`mouse_gene_accession_id`) between 9 and 11))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`parameter` definition

CREATE TABLE `parameter` (
  `parameter_stable_id` char(20) NOT NULL,
  `parameter_name` char(200) DEFAULT NULL,
  `impc_origin_id` int DEFAULT NULL,
  `parameter_description` varchar(1000) DEFAULT NULL,
  PRIMARY KEY (`parameter_stable_id`),
  CONSTRAINT `chk_parameter_name` CHECK ((char_length(`parameter_name`) between 2 and 200)),
  CONSTRAINT `chk_parameter_stable_id` CHECK ((char_length(`parameter_name`) between 15 and 20))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.tissue definition

CREATE TABLE `tissue` (
  `tissue_id` int unsigned NOT NULL AUTO_INCREMENT,
  `tissue_name` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`tissue_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`human gene` definition

CREATE TABLE `human gene` (
  `hgnc_id` char(10) NOT NULL,
  `human_gene_symbol` varchar(255) DEFAULT NULL,
  `human_gene_name` text,
  `mouse_gene_accession_id` char(11) NOT NULL,
  PRIMARY KEY (`hgnc_id`),
  UNIQUE KEY `unq_human gene_mouse_gene_accession_id` (`mouse_gene_accession_id`),
  CONSTRAINT `fk_human gene_mouse gene` FOREIGN KEY (`mouse_gene_accession_id`) REFERENCES `mouse gene` (`mouse_gene_accession_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`mouse gene product` definition

CREATE TABLE `mouse gene product` (
  `mouse_gene_product_id` char(10) NOT NULL,
  `mouse_gene_product_source` char(9) DEFAULT NULL,
  `mouse_gene_product_name` varchar(255) DEFAULT NULL,
  `mouse_gene_accession_id` char(11) NOT NULL,
  PRIMARY KEY (`mouse_gene_product_id`),
  KEY `fk_mouse gene product_mouse gene` (`mouse_gene_accession_id`),
  CONSTRAINT `fk_mouse gene product_mouse gene` FOREIGN KEY (`mouse_gene_accession_id`) REFERENCES `mouse gene` (`mouse_gene_accession_id`),
  CONSTRAINT `cns_mouse gene product` CHECK ((char_length(`mouse_gene_product_id`) in (6, 10)))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`mouse genotype` definition

CREATE TABLE `mouse genotype` (
  `mouse_genotype_id` int unsigned NOT NULL AUTO_INCREMENT,
  `allele_symbol` char(35) DEFAULT NULL,
  `strain_name` char(26) DEFAULT NULL,
  `mouse_gene_accession_id` char(11) NOT NULL,
  PRIMARY KEY (`mouse_genotype_id`),
  KEY `fk_mouse genotype_mouse gene` (`mouse_gene_accession_id`),
  CONSTRAINT `fk_mouse genotype_mouse gene` FOREIGN KEY (`mouse_gene_accession_id`) REFERENCES `mouse gene` (`mouse_gene_accession_id`),
  CONSTRAINT `chk_strain_name` CHECK ((char_length(`strain_name`) between 3 and 26)),
  CONSTRAINT `cns_mouse genotype` CHECK ((char_length(`allele_symbol`) between 10 and 35))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`parameter group` definition

CREATE TABLE `parameter group` (
  `parameter_stable_id` char(20) NOT NULL,
  `group_id` int unsigned NOT NULL,
  PRIMARY KEY (`parameter_stable_id`, `group_id`),
  KEY `fk_parameter_groups_groups` (`group_id`),
  CONSTRAINT `fk_parameter_groups_groups` FOREIGN KEY (`group_id`) REFERENCES `group` (`group_id`),
  CONSTRAINT `fk_parameter_groups_parameter` FOREIGN KEY (`parameter_stable_id`) REFERENCES `parameter` (`parameter_stable_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`query gene` definition

CREATE TABLE `query gene` (
  `query_gene_id` int unsigned NOT NULL AUTO_INCREMENT,
  `query_gene_name` varchar(100) DEFAULT NULL,
  `mouse_gene_accession_id` char(11) NOT NULL,
  PRIMARY KEY (`query_gene_id`),
  UNIQUE KEY `unq_query gene_mouse_gene_accession_id` (`mouse_gene_accession_id`),
  CONSTRAINT `fk_query gene_mouse gene` FOREIGN KEY (`mouse_gene_accession_id`) REFERENCES `mouse gene` (`mouse_gene_accession_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`raw analysis data` definition

CREATE TABLE `raw analysis data` (
  `analysis_id` char(12) NOT NULL,
  `mouse_life_stage` char(17) DEFAULT NULL,
  `pvalue` float DEFAULT NULL,
  `parameter_stable_id` char(20) NOT NULL,
  `mouse_genotype_id` int unsigned NOT NULL,
  PRIMARY KEY (`analysis_id`),
  KEY `fk_raw analysis data_parameter` (`parameter_stable_id`),
  KEY `fk_raw analysis data_mouse genotype` (`mouse_genotype_id`),
  CONSTRAINT `fk_raw analysis data_mouse genotype` FOREIGN KEY (`mouse_genotype_id`) REFERENCES `mouse genotype` (`mouse_genotype_id`),
  CONSTRAINT `fk_raw analysis data_parameter` FOREIGN KEY (`parameter_stable_id`) REFERENCES `parameter` (`parameter_stable_id`),
  CONSTRAINT `chk_analysis_id` CHECK ((char_length(`analysis_id`) = 12)),
  CONSTRAINT `chk_mouse_life_stage` CHECK ((char_length(`mouse_life_stage`) between 4 and 17))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`disease association` definition

CREATE TABLE `disease association` (
  `hgnc_id` char(10) NOT NULL,
  `do_term_id` char(12) NOT NULL,
  PRIMARY KEY (`hgnc_id`, `do_term_id`),
  KEY `fk_disease_association_disease ontology term` (`do_term_id`),
  CONSTRAINT `fk_disease_association_disease ontology term` FOREIGN KEY (`do_term_id`) REFERENCES `disease ontology term` (`do_term_id`),
  CONSTRAINT `fk_disease_association_human gene` FOREIGN KEY (`hgnc_id`) REFERENCES `human gene` (`hgnc_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`go annotation` definition

CREATE TABLE `go annotation` (
  `annotation_id` int unsigned NOT NULL AUTO_INCREMENT,
  `annotation_date` date DEFAULT NULL,
  `assigned_by` varchar(100) DEFAULT NULL,
  `evidence_code` char(3) DEFAULT NULL,
  `qualifier` varchar(255) DEFAULT NULL,
  `mouse_gene_product_id` char(10) NOT NULL,
  `go_term_id` char(10) NOT NULL,
  `reference_id` int unsigned NOT NULL,
  PRIMARY KEY (`annotation_id`),
  KEY `fk_go annotation_mouse gene product` (`mouse_gene_product_id`),
  KEY `fk_go annotation_gene ontology term` (`go_term_id`),
  KEY `fk_go annotation_go annotation references` (`reference_id`),
  CONSTRAINT `fk_go annotation_gene ontology term` FOREIGN KEY (`go_term_id`) REFERENCES `gene ontology term` (`go_term_id`),
  CONSTRAINT `fk_go annotation_go annotation references` FOREIGN KEY (`reference_id`) REFERENCES `go annotation references` (`reference_id`),
  CONSTRAINT `fk_go annotation_mouse gene product` FOREIGN KEY (`mouse_gene_product_id`) REFERENCES `mouse gene product` (`mouse_gene_product_id`),
  CONSTRAINT `cns_go annotation` CHECK ((char_length(`mouse_gene_product_id`) in (6, 10)))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`go annotations and extensions` definition

CREATE TABLE `go annotations and extensions` (
  `annotation_extension_id` int unsigned NOT NULL,
  `annotation_id` int unsigned NOT NULL,
  PRIMARY KEY (`annotation_extension_id`, `annotation_id`),
  KEY `fk_go annotations and extensions_go annotation` (`annotation_id`),
  CONSTRAINT `fk_go annotations and extensions_annotation extension` FOREIGN KEY (`annotation_extension_id`) REFERENCES `annotation extension` (`annotation_extension_id`),
  CONSTRAINT `fk_go annotations and extensions_go annotation` FOREIGN KEY (`annotation_id`) REFERENCES `go annotation` (`annotation_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.go_with_from definition

CREATE TABLE `go_with_from` (
  `with_from_id` int NOT NULL,
  `annotation_id` int unsigned NOT NULL,
  PRIMARY KEY (`with_from_id`, `annotation_id`),
  KEY `fk_go_wtih_from_go annotation` (`annotation_id`),
  CONSTRAINT `fk_go_wtih_from_go annotation` FOREIGN KEY (`annotation_id`) REFERENCES `go annotation` (`annotation_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
-- impc.`lacz expression` definition

CREATE TABLE `lacz expression` (
  `lacz_expression_id` int unsigned NOT NULL AUTO_INCREMENT,
  `lacz_expression_value` char(19) DEFAULT NULL,
  `tissue_id` int unsigned NOT NULL,
  `analysis_id` char(12) NOT NULL,
  PRIMARY KEY (`lacz_expression_id`),
  KEY `fk_lacz expression_tissue` (`tissue_id`),
  KEY `fk_lacz expression_raw analysis data` (`analysis_id`),
  CONSTRAINT `fk_lacz expression_raw analysis data` FOREIGN KEY (`analysis_id`) REFERENCES `raw analysis data` (`analysis_id`),
  CONSTRAINT `fk_lacz expression_tissue` FOREIGN KEY (`tissue_id`) REFERENCES `tissue` (`tissue_id`),
  CONSTRAINT `chk_lacz_expression_value` CHECK ((char_length(`lacz_expression_value`) between 2 and 200))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
