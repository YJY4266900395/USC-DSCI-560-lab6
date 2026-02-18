CREATE TABLE production_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    well_id INT,
    well_status VARCHAR(100),
    well_type VARCHAR(100),
    closest_city VARCHAR(255),
    oil_barrels DOUBLE,
    gas_mcf DOUBLE,
    FOREIGN KEY (well_id) REFERENCES wells(id)
);

