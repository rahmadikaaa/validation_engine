CREATE OR REPLACE TABLE `charged-camera-310217.validation_engine.items_enriched_v1` AS
SELECT
  id_item,
  nama_barang,

  TRIM(
    REGEXP_REPLACE(
      REGEXP_REPLACE(
        REGEXP_REPLACE(
          REGEXP_REPLACE(
            LOWER(CONCAT(nama_barang, " ", spesifikasi)),
            r'tubbless|tubless',
            'tubeless'
          ),
          r'\buk\.',
          'ukuran'
        ),
        r'r22,5',
        'r22.5'
      ),
      r'\s+',
      ' '
    )
  ) AS normalized_query,

  spesifikasi AS raw_specs,

  CASE
    WHEN LOWER(nama_barang) LIKE '%ban%' THEN 'tire'
    WHEN LOWER(nama_barang) LIKE '%kontainer%' THEN 'container'
    WHEN LOWER(nama_barang) LIKE '%mesin%' THEN 'machine'
    ELSE 'general'
  END AS item_type,

  CASE
    WHEN LOWER(spesifikasi) LIKE '%tubbless%' THEN 'needs_typo_normalization'
    WHEN LOWER(spesifikasi) LIKE '%dimensi%' THEN 'dimension_sensitive'
    ELSE 'ready_for_search'
  END AS validation_readiness,

  0.80 AS confidence

FROM `charged-camera-310217.validation_engine.items_raw`;
