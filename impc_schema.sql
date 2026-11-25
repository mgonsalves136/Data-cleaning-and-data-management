CREATE SCHEMA impc;

---------------------------------------------------
---            annotation extension             ---
---------------------------------------------------
CREATE  TABLE impc.`annotation extension` ( 
	annotation_extension_id INT UNSIGNED  NOT NULL  AUTO_INCREMENT  PRIMARY KEY,
	annotation_extension_name VARCHAR(1000)       
 ) engine=InnoDB;

---------------------------------------------------
---            disease ontology term            ---
---------------------------------------------------
CREATE  TABLE impc.`disease ontology term` ( 
	do_term_id           CHAR(12)   NOT NULL    PRIMARY KEY,
	do_term_name         TEXT       
 ) engine=InnoDB;

---------------------------------------------------
---             gene ontology term              ---
---------------------------------------------------
CREATE  TABLE impc.`gene ontology term` ( 
	go_term_id           CHAR(10)   NOT NULL    PRIMARY KEY,
	go_aspect            CHAR(1)       
 ) engine=InnoDB;

---------------------------------------------------
---          go annotation references           ---
---------------------------------------------------
CREATE  TABLE impc.`go annotation references` ( 
	reference_id         INT UNSIGNED  NOT NULL  AUTO_INCREMENT  PRIMARY KEY,
	reference_code       VARCHAR(255)       
 ) engine=InnoDB;

---------------------------------------------------
---                    group                    ---
---------------------------------------------------
CREATE  TABLE impc.`group` ( 
	group_id             INT UNSIGNED  NOT NULL  AUTO_INCREMENT  PRIMARY KEY,
	group_name           VARCHAR(100)       
 ) engine=InnoDB;

---------------------------------------------------
---                 mouse gene                  ---
---------------------------------------------------
CREATE  TABLE impc.`mouse gene` ( 
	mouse_gene_accession_id CHAR(11)   NOT NULL    PRIMARY KEY,
	mouse_gene_symbol    CHAR(13)       
 ) engine=InnoDB;

ALTER TABLE impc.`mouse gene` ADD CONSTRAINT `chk_mouse gene_symbol` CHECK ( char_length(`mouse_gene_symbol`) between 1 and 13 );

ALTER TABLE impc.`mouse gene` ADD CONSTRAINT chk_mouse_gene_accession_id CHECK ( char_length(`mouse_gene_accession_id`) between 9 and 11 );

---------------------------------------------------
---                 human gene                  ---
---------------------------------------------------
CREATE  TABLE impc.`human gene` ( 
	hgnc_id              CHAR(10)   NOT NULL    PRIMARY KEY,
	human_gene_symbol    VARCHAR(255)       ,
	human_gene_name      TEXT       ,
	mouse_gene_accession_id CHAR(11)   NOT NULL    ,
	CONSTRAINT `unq_human gene_mouse_gene_accession_id` UNIQUE ( mouse_gene_accession_id ) ,
	CONSTRAINT `fk_human gene_mouse gene` FOREIGN KEY ( mouse_gene_accession_id ) REFERENCES impc.`mouse gene`( mouse_gene_accession_id ) ON DELETE NO ACTION ON UPDATE NO ACTION
 ) engine=InnoDB;

---------------------------------------------------
---             disease association             ---
---------------------------------------------------
CREATE  TABLE impc.`disease association` ( 
	hgnc_id              CHAR(10)   NOT NULL    ,
	do_term_id           CHAR(12)   NOT NULL    ,
	CONSTRAINT `pk_disease association` PRIMARY KEY ( hgnc_id, do_term_id ),
	CONSTRAINT `fk_disease_association_disease ontology term` FOREIGN KEY ( do_term_id ) REFERENCES impc.`disease ontology term`( do_term_id ) ON DELETE NO ACTION ON UPDATE NO ACTION,
	CONSTRAINT `fk_disease_association_human gene` FOREIGN KEY ( hgnc_id ) REFERENCES impc.`human gene`( hgnc_id ) ON DELETE NO ACTION ON UPDATE NO ACTION
 ) engine=InnoDB;

CREATE INDEX `fk_disease_association_disease ontology term` ON impc.`disease association` ( do_term_id );

---------------------------------------------------
---             mouse gene product              ---
---------------------------------------------------
CREATE  TABLE impc.`mouse gene product` ( 
	mouse_gene_product_id CHAR(10)   NOT NULL    PRIMARY KEY,
	mouse_gene_product_source CHAR(9)       ,
	mouse_gene_product_name VARCHAR(255)       ,
	mouse_gene_accession_id CHAR(11)   NOT NULL    ,
	CONSTRAINT `fk_mouse gene product_mouse gene` FOREIGN KEY ( mouse_gene_accession_id ) REFERENCES impc.`mouse gene`( mouse_gene_accession_id ) ON DELETE NO ACTION ON UPDATE NO ACTION
 ) engine=InnoDB;

ALTER TABLE impc.`mouse gene product` ADD CONSTRAINT `cns_mouse gene product` CHECK ( char_length(`mouse_gene_product_id`) in (6,10) );

CREATE INDEX `fk_mouse gene product_mouse gene` ON impc.`mouse gene product` ( mouse_gene_accession_id );

---------------------------------------------------
---                go annotation                ---
---------------------------------------------------
CREATE  TABLE impc.`go annotation` ( 
	annotation_id        INT UNSIGNED  NOT NULL  AUTO_INCREMENT  PRIMARY KEY,
	qualifier            VARCHAR(255)       ,
	evidence_code        CHAR(3)       ,
	assigned_by          VARCHAR(100)       ,
	annotation_date      DATE       ,
	mouse_gene_product_id CHAR(10)   NOT NULL    ,
	go_term_id           CHAR(10)   NOT NULL    ,
	reference_id         INT UNSIGNED  NOT NULL    ,
	CONSTRAINT `fk_go annotation_mouse gene product` FOREIGN KEY ( mouse_gene_product_id ) REFERENCES impc.`mouse gene product`( mouse_gene_product_id ) ON DELETE NO ACTION ON UPDATE NO ACTION,
	CONSTRAINT `fk_go annotation_gene ontology term` FOREIGN KEY ( go_term_id ) REFERENCES impc.`gene ontology term`( go_term_id ) ON DELETE NO ACTION ON UPDATE NO ACTION,
	CONSTRAINT `fk_go annotation_go annotation references` FOREIGN KEY ( reference_id ) REFERENCES impc.`go annotation references`( reference_id ) ON DELETE NO ACTION ON UPDATE NO ACTION
 ) engine=InnoDB;

ALTER TABLE impc.`go annotation` ADD CONSTRAINT `cns_go annotation` CHECK ( char_length(`mouse_gene_product_id`) in (6,10) );

CREATE INDEX `fk_go annotation_mouse gene product` ON impc.`go annotation` ( mouse_gene_product_id );

CREATE INDEX `fk_go annotation_gene ontology term` ON impc.`go annotation` ( go_term_id );

CREATE INDEX `fk_go annotation_go annotation references` ON impc.`go annotation` ( reference_id );

---------------------------------------------------
---        go annotations and extensions        ---
---------------------------------------------------
CREATE  TABLE impc.`go annotations and extensions` ( 
	annotation_extension_id INT UNSIGNED  NOT NULL    ,
	annotation_id        INT UNSIGNED  NOT NULL    ,
	CONSTRAINT `pk_go annotations and extensions` PRIMARY KEY ( annotation_extension_id, annotation_id ),
	CONSTRAINT `fk_go annotations and extensions_go annotation` FOREIGN KEY ( annotation_id ) REFERENCES impc.`go annotation`( annotation_id ) ON DELETE NO ACTION ON UPDATE NO ACTION,
	CONSTRAINT `fk_go annotations and extensions_annotation extension` FOREIGN KEY ( annotation_extension_id ) REFERENCES impc.`annotation extension`( annotation_extension_id ) ON DELETE NO ACTION ON UPDATE NO ACTION
 ) engine=InnoDB;

CREATE INDEX `fk_go annotations and extensions_go annotation` ON impc.`go annotations and extensions` ( annotation_id );

---------------------------------------------------
---                go_with_from                 ---
---------------------------------------------------
CREATE  TABLE impc.go_with_from ( 
	annotation_id        INT UNSIGNED  NOT NULL    ,
	with_from_id         VARCHAR(100)   NOT NULL    ,
	CONSTRAINT pk_go_with_from PRIMARY KEY ( with_from_id, annotation_id ),
	CONSTRAINT `fk_go_wtih_from_go annotation` FOREIGN KEY ( annotation_id ) REFERENCES impc.`go annotation`( annotation_id ) ON DELETE NO ACTION ON UPDATE NO ACTION
 ) engine=InnoDB;

CREATE INDEX `fk_go_wtih_from_go annotation` ON impc.go_with_from ( annotation_id );

---------------------------------------------------
---               mouse genotype                ---
---------------------------------------------------
CREATE  TABLE impc.`mouse genotype` ( 
	mouse_genotype_id    INT UNSIGNED  NOT NULL  AUTO_INCREMENT  PRIMARY KEY,
	allele_symbol        CHAR(35)       ,
	strain_name          CHAR(26)       ,
	mouse_gene_accession_id CHAR(11)   NOT NULL    ,
	CONSTRAINT `fk_mouse genotype_mouse gene` FOREIGN KEY ( mouse_gene_accession_id ) REFERENCES impc.`mouse gene`( mouse_gene_accession_id ) ON DELETE NO ACTION ON UPDATE NO ACTION
 ) engine=InnoDB;

ALTER TABLE impc.`mouse genotype` ADD CONSTRAINT chk_allele_symbol CHECK ( CHAR_LENGTH(allele_symbol) BETWEEN 10 AND 35 );

ALTER TABLE impc.`mouse genotype` ADD CONSTRAINT chk_strain_name CHECK ( char_length(`strain_name`) between 3 and 26 );

ALTER TABLE impc.`mouse genotype` ADD CONSTRAINT `cns_mouse genotype` CHECK ( char_length(`allele_symbol`) between 10 and 35 );

CREATE INDEX `fk_mouse genotype_mouse gene` ON impc.`mouse genotype` ( mouse_gene_accession_id );

---------------------------------------------------
---                  parameter                  ---
---------------------------------------------------
CREATE  TABLE impc.parameter ( 
	parameter_stable_id  CHAR(20)   NOT NULL    PRIMARY KEY,
	impc_origin_id       INT       ,
	parameter_name       CHAR(200)       ,
	parameter_description TEXT       
 ) engine=InnoDB;

ALTER TABLE impc.parameter ADD CONSTRAINT chk_parameter_name CHECK ( char_length(`parameter_name`) between 2 and 200 );

ALTER TABLE impc.parameter ADD CONSTRAINT chk_parameter_stable_id CHECK ( char_length(`parameter_stable_id`) between 15 and 20 );

---------------------------------------------------
---               parameter group               ---
---------------------------------------------------
CREATE  TABLE impc.`parameter group` ( 
	parameter_stable_id  CHAR(20)   NOT NULL    ,
	group_id             INT UNSIGNED  NOT NULL    ,
	CONSTRAINT `pk_parameter group` PRIMARY KEY ( parameter_stable_id, group_id ),
	CONSTRAINT fk_parameter_groups_parameter FOREIGN KEY ( parameter_stable_id ) REFERENCES impc.parameter( parameter_stable_id ) ON DELETE NO ACTION ON UPDATE NO ACTION,
	CONSTRAINT fk_parameter_groups_groups FOREIGN KEY ( group_id ) REFERENCES impc.`group`( group_id ) ON DELETE NO ACTION ON UPDATE NO ACTION
 ) engine=InnoDB;

CREATE INDEX fk_parameter_groups_groups ON impc.`parameter group` ( group_id );

---------------------------------------------------
---                  procedure                  ---
---------------------------------------------------
CREATE  TABLE impc.`procedure` ( 
	procedure_id         INT UNSIGNED  NOT NULL  AUTO_INCREMENT  PRIMARY KEY,
	procedure_name       VARCHAR(255)   NOT NULL    ,
	procedure_description TEXT       ,
	is_mandatory         BOOLEAN   NOT NULL    ,
	CONSTRAINT uq_procedure_name_mandatory UNIQUE ( procedure_name, is_mandatory ) 
 ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

---------------------------------------------------
---           parameter and procedure           ---
---------------------------------------------------
CREATE  TABLE impc.`parameter and procedure` ( 
	procedure_id         INT UNSIGNED  NOT NULL    ,
	parameter_stable_id  CHAR(20)   NOT NULL    ,
	CONSTRAINT `pk_parameter and procedure` PRIMARY KEY ( procedure_id, parameter_stable_id ),
	CONSTRAINT fk_pp_parameter FOREIGN KEY ( parameter_stable_id ) REFERENCES impc.parameter( parameter_stable_id ) ON DELETE NO ACTION ON UPDATE NO ACTION,
	CONSTRAINT fk_pp_procedure FOREIGN KEY ( procedure_id ) REFERENCES impc.`procedure`( procedure_id ) ON DELETE NO ACTION ON UPDATE NO ACTION
 ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX fk_pp_parameter ON impc.`parameter and procedure` ( parameter_stable_id );

---------------------------------------------------
---                 query gene                  ---
---------------------------------------------------
CREATE  TABLE impc.`query gene` ( 
	query_gene_id        INT UNSIGNED  NOT NULL  AUTO_INCREMENT  PRIMARY KEY,
	query_gene_name      VARCHAR(100)       ,
	mouse_gene_accession_id CHAR(11)   NOT NULL    ,
	CONSTRAINT `unq_query gene_mouse_gene_accession_id` UNIQUE ( mouse_gene_accession_id ) ,
	CONSTRAINT `fk_query gene_mouse gene` FOREIGN KEY ( mouse_gene_accession_id ) REFERENCES impc.`mouse gene`( mouse_gene_accession_id ) ON DELETE NO ACTION ON UPDATE NO ACTION
 ) engine=InnoDB;

---------------------------------------------------
---                   tissue                    ---
---------------------------------------------------
CREATE  TABLE impc.tissue ( 
	tissue_id            INT UNSIGNED  NOT NULL  AUTO_INCREMENT  PRIMARY KEY,
	tissue_name          VARCHAR(100)       
 ) engine=InnoDB;

---------------------------------------------------
---               lacz expression               ---
---------------------------------------------------
CREATE  TABLE impc.`lacz expression` ( 
	lacz_expression_id   INT UNSIGNED  NOT NULL  AUTO_INCREMENT  PRIMARY KEY,
	lacz_expression_value CHAR(19)       ,
	tissue_id            INT UNSIGNED  NOT NULL    ,
	analysis_id          CHAR(12)   NOT NULL    ,
	CONSTRAINT `fk_lacz expression_tissue` FOREIGN KEY ( tissue_id ) REFERENCES impc.tissue( tissue_id ) ON DELETE NO ACTION ON UPDATE NO ACTION
 ) engine=InnoDB;

ALTER TABLE impc.`lacz expression` ADD CONSTRAINT chk_lacz_expression_value CHECK ( char_length(`lacz_expression_value`) between 2 and 200 );

CREATE INDEX `fk_lacz expression_tissue` ON impc.`lacz expression` ( tissue_id );

CREATE INDEX `fk_lacz expression_raw analysis data` ON impc.`lacz expression` ( analysis_id );

