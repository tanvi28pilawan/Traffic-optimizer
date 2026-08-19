import { useState, useEffect, useRef } from "react";
import axios from "axios";

export default function LocationInput({ label, placeholder, value, onChange, city }) {
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (value.length < 3) {
      setSuggestions([]);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const cityShort = city ? city.split(",")[0].trim() : "";
const query = cityShort ? `${value}, ${cityShort}` : `${value}, India`;
        const res = await axios.get(
          `https://nominatim.openstreetmap.org/search`,
          {
            params: {
              q: query,
              format: "json",
              limit: 5,
              addressdetails: 1,
            },
            headers: {
              "Accept-Language": "en",
            },
          }
        );
        setSuggestions(res.data);
        setShowSuggestions(true);
      } catch (err) {
        console.error("Nominatim error:", err);
      }
      setSearching(false);
    }, 500);
  }, [value, city]);

  const handleSelect = (suggestion) => {
    onChange(suggestion.display_name.split(",")[0]);
    setSuggestions([]);
    setShowSuggestions(false);
  };

  return (
    <div className="sidebar-field location-field">
      <label className="sidebar-label">{label}</label>
      <div className="location-input-wrap">
        <input
          className="sidebar-input"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
          autoComplete="off"
        />
        {searching && <span className="location-searching">...</span>}
      </div>

      {showSuggestions && suggestions.length > 0 && (
        <div className="suggestions-list">
          {suggestions.map((s, i) => {
            const parts = s.display_name.split(",");
            const main = parts[0];
            const sub = parts.slice(1, 3).join(",");
            return (
              <button
                key={i}
                className="suggestion-item"
                onMouseDown={() => handleSelect(s)}
              >
                <span className="suggestion-icon">📍</span>
                <div className="suggestion-text">
                  <span className="suggestion-main">{main}</span>
                  <span className="suggestion-sub">{sub}</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}