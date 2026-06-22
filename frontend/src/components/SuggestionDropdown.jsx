export default function SuggestionDropdown({
  isOpen,
  suggestions,
  highlightedIndex,
  isLoading,
  onSelect,
  onHover,
}) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="suggestion-dropdown" role="listbox" aria-label="Typeahead suggestions">
      {isLoading && <div className="suggestion-state">Loading suggestions</div>}

      {!isLoading && suggestions.length === 0 && (
        <div className="suggestion-state">No suggestions found</div>
      )}

      {!isLoading &&
        suggestions.map((suggestion, index) => (
          <button
            type="button"
            className={`suggestion-item ${highlightedIndex === index ? 'is-highlighted' : ''}`}
            key={suggestion}
            role="option"
            aria-selected={highlightedIndex === index}
            onMouseEnter={() => onHover(index)}
            onMouseDown={(event) => {
              event.preventDefault();
              onSelect(suggestion);
            }}
          >
            <span className="suggestion-icon" aria-hidden="true" />
            <span>{suggestion}</span>
          </button>
        ))}
    </div>
  );
}
