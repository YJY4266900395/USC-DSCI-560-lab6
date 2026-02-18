CREATE TABLE stimulation_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    well_id INT,
    treatment_type VARCHAR(255),
    total_proppant DOUBLE,
    fluid_volume DOUBLE,
    max_pressure DOUBLE,
    FOREIGN KEY (well_id) REFERENCES wells(id)
);
