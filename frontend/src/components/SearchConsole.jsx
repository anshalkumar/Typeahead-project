import { useEffect, useMemo, useRef, useState } from 'react';
import { fetchSuggestions, submitSearch } from '../lib/api.js';
import { useDebouncedValue } from '../hooks/useDebouncedValue.js';
import SuggestionDropdown from './SuggestionDropdown.jsx';

export default function SearchConsole({ onError }) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isDropdownOpen, setDropdownOpen] = useState(false);
  const [isSuggestLoading, setSuggestLoading] = useState(false);
  const [isSearching, setSearching] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [searchStatus, setSearchStatus] = useState('');
  const [latency, setLatency] = useState(null);
  const requestIdRef = useRef(0);
  const debouncedQuery = useDebouncedValue(query, 300);

  const trimmedQuery = useMemo(() => query.trim(), [query]);

  useEffect(() => {
    const prefix = debouncedQuery.trim();
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;

    if (!prefix) {
      setSuggestions([]);
      setDropdownOpen(false);
      setHighlightedIndex(-1);
      return;
    }

    setSuggestLoading(true);
    setDropdownOpen(true);

    fetchSuggestions(prefix)
      .then(({ data, latency: suggestionLatency }) => {
        if (requestIdRef.current !== requestId) {
          return;
        }

        const nextSuggestions = Array.isArray(data.suggestions) ? data.suggestions : [];
        setSuggestions(nextSuggestions);
        setHighlightedIndex(-1);
        setLatency(suggestionLatency);
      })
      .catch((error) => {
        if (requestIdRef.current !== requestId) {
          return;
        }

        setSuggestions([]);
        setHighlightedIndex(-1);
        onError(error.message || 'Unable to fetch suggestions');
      })
      .finally(() => {
        if (requestIdRef.current === requestId) {
          setSuggestLoading(false);
        }
      });
  }, [debouncedQuery, onError]);

  async function runSearch(nextQuery = trimmedQuery) {
    const searchQuery = nextQuery.trim();
    if (!searchQuery) {
      return;
    }

    setDropdownOpen(false);
    setSearching(true);
    setSearchStatus('');

    try {
      const { latency: searchLatency } = await submitSearch(searchQuery);
      setLatency(searchLatency);
      setSearchStatus('Searched');
    } catch (error) {
      onError(error.message || 'Unable to submit search');
    } finally {
      setSearching(false);
    }
  }

  function selectSuggestion(suggestion) {
    setQuery(suggestion);
    setDropdownOpen(false);
    setSuggestions([]);
    setHighlightedIndex(-1);
    runSearch(suggestion);
  }

  function handleKeyDown(event) {
    if (event.key === 'Escape') {
      setDropdownOpen(false);
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (suggestions.length === 0) {
        return;
      }
      setDropdownOpen(true);
      setHighlightedIndex((current) => (current + 1) % suggestions.length);
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (suggestions.length === 0) {
        return;
      }
      setDropdownOpen(true);
      setHighlightedIndex((current) =>
        current <= 0 ? suggestions.length - 1 : current - 1,
      );
      return;
    }

    if (event.key === 'Enter') {
      event.preventDefault();
      if (isDropdownOpen && highlightedIndex >= 0 && suggestions[highlightedIndex]) {
        selectSuggestion(suggestions[highlightedIndex]);
      } else {
        runSearch();
      }
    }
  }

  return (
    <section className="search-console" aria-label="Typeahead search">
      <h1>Typeahead Search</h1>

      <form
        className="search-shell"
        onSubmit={(event) => {
          event.preventDefault();
          runSearch();
        }}
      >
        <div className="search-input-wrap">
          <span className="search-glyph" aria-hidden="true" />
          <input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setSearchStatus('');
            }}
            onFocus={() => {
              if (trimmedQuery) {
                setDropdownOpen(true);
              }
            }}
            onKeyDown={handleKeyDown}
            placeholder="Start typing..."
            aria-label="Search query"
            aria-autocomplete="list"
            aria-expanded={isDropdownOpen}
          />
          <SuggestionDropdown
            isOpen={isDropdownOpen && trimmedQuery.length > 0}
            suggestions={suggestions}
            highlightedIndex={highlightedIndex}
            isLoading={isSuggestLoading}
            onSelect={selectSuggestion}
            onHover={setHighlightedIndex}
          />
        </div>

        <button
          type="submit"
          className="search-button"
          disabled={!trimmedQuery || isSearching}
        >
          {isSearching ? 'Searching...' : 'Search'}
        </button>
      </form>

      <div className="search-meta" aria-live="polite">
        <p className={`search-status ${searchStatus ? 'is-visible' : ''}`}>
          <span className="status-indicator" />
          {searchStatus || 'Searched'}
        </p>
        <p className="latency">
          <span>Latency</span>
          <span className={`latency-badge ${latency === null ? '' : latency < 30 ? 'fast' : latency < 100 ? 'medium' : 'slow'}`}>
            {latency === null ? '--' : `${latency} ms`}
          </span>
        </p>
      </div>
    </section>
  );
}
