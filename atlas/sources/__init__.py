"""
Builders that turn raw rows/responses from the three incoming sources into
the typed field values the v2 schema expects. The scale-out task fetches the
raw data and calls these; the shapes here were designed against the real
files/API responses (see tests/fixtures/sources/).

  faers.build_faers_summary          openFDA drug/event.json  -> real_world_safety.faers_summary
  orange_book.build_orange_book_record  products/patent/exclusivity.txt -> exclusivity.orange_book
  purple_book.build_purple_book_record  Purple Book monthly CSV -> exclusivity.purple_book
"""
