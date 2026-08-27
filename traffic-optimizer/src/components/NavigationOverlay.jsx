import { useEffect, useRef, useState } from "react";

const TURN_ICON = {
  "Turn left": "↰",
  "Turn right": "↱",
  "Make a U-turn": "↶",
  "Start your journey": "↑",
  "You have arrived at your destination!": "🏁",
};

function formatDistance(m) {
  if (m == null) return "";

  if (m < 1000) {
    return `${Math.round(m)} m`;
  }

  return `${(m / 1000).toFixed(1)} km`;
}

function getTurnClass(instruction = "") {
  const text = instruction.toLowerCase();

  if (text.includes("left")) return "left";
  if (text.includes("right")) return "right";
  if (text.includes("u-turn")) return "uturn";
  if (text.includes("arrived")) return "arrival";

  return "straight";
}

function getDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;

  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;

  return (
    R *
    2 *
    Math.atan2(
      Math.sqrt(a),
      Math.sqrt(1 - a)
    )
  );
}

export default function NavigationOverlay({
  route,
  mode,
  gpsLocation,
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [voiceEnabled, setVoiceEnabled] = useState(true);

  const announcedSteps = useRef(new Set());

  const directions = route?.directions || [];

  const current = directions[activeIndex];
  const next = directions[activeIndex + 1];

  // Reset when a new route is created
  useEffect(() => {
    setActiveIndex(0);
    announcedSteps.current.clear();
  }, [route]);

  // --------------------------------------------------
  // LIVE DISTANCE TO CURRENT TURN
  // --------------------------------------------------

  let distanceToTurn = null;

  if (
    gpsLocation &&
    current &&
    current.lat != null &&
    current.lon != null
  ) {
    distanceToTurn = getDistanceMeters(
      gpsLocation[0],
      gpsLocation[1],
      current.lat,
      current.lon
    );
  }

  // --------------------------------------------------
  // AUTOMATIC GPS STEP CHANGE
  // --------------------------------------------------

  useEffect(() => {
    if (!gpsLocation || !current) return;

    if (
      current.lat == null ||
      current.lon == null
    ) {
      return;
    }

    const distance = getDistanceMeters(
      gpsLocation[0],
      gpsLocation[1],
      current.lat,
      current.lon
    );

    console.log(
      `Step ${activeIndex + 1}: ${Math.round(distance)}m`
    );

    const isArrival =
      current.instruction
        ?.toLowerCase()
        .includes("arrived");

    // Arrival should only trigger near destination
    if (isArrival) {
      return;
    }

    // Automatically move to next instruction
    // when user reaches current turn
    if (distance <= 30) {
      if (activeIndex < directions.length - 1) {
        setActiveIndex((prev) => prev + 1);
      }
    }
  }, [
    gpsLocation,
    current,
    activeIndex,
    directions.length,
  ]);

  // --------------------------------------------------
  // VOICE
  // --------------------------------------------------

  useEffect(() => {
    if (!current || !voiceEnabled) return;

    if (!("speechSynthesis" in window)) return;

    const isArrival =
      current.instruction
        ?.toLowerCase()
        .includes("arrived");

    // Don't announce arrival automatically
    // until GPS is actually near destination
    if (isArrival) {
      if (
        distanceToTurn == null ||
        distanceToTurn > 40
      ) {
        return;
      }
    }

    if (
      announcedSteps.current.has(activeIndex)
    ) {
      return;
    }

    announcedSteps.current.add(activeIndex);

    window.speechSynthesis.cancel();

    let text = current.instruction;

    if (
      !isArrival &&
      distanceToTurn != null
    ) {
      text = `${current.instruction} in ${formatDistance(
        distanceToTurn
      )}`;
    }

    const utterance =
      new SpeechSynthesisUtterance(text);

    utterance.rate = 0.95;
    utterance.pitch = 1;
    utterance.volume = 1;

    window.speechSynthesis.speak(utterance);
  }, [
    activeIndex,
    current,
    voiceEnabled,
    gpsLocation,
    distanceToTurn,
  ]);

  // --------------------------------------------------
  // MANUAL VOICE
  // --------------------------------------------------

  const handleVoice = () => {
    if (!current) return;

    if (!("speechSynthesis" in window)) return;

    window.speechSynthesis.cancel();

    const isArrival =
      current.instruction
        ?.toLowerCase()
        .includes("arrived");

    let text = current.instruction;

    if (
      !isArrival &&
      distanceToTurn != null
    ) {
      text = `${current.instruction} in ${formatDistance(
        distanceToTurn
      )}`;
    }

    const utterance =
      new SpeechSynthesisUtterance(text);

    utterance.rate = 0.95;
    utterance.pitch = 1;
    utterance.volume = 1;

    window.speechSynthesis.speak(utterance);
  };

  // --------------------------------------------------
  // BACK
  // --------------------------------------------------

  const handleBack = () => {
    if (activeIndex <= 0) return;

    setActiveIndex((prev) => prev - 1);
  };

  // --------------------------------------------------
  // NEXT
  // --------------------------------------------------

  const handleNext = () => {
    if (
      activeIndex >=
      directions.length - 1
    ) {
      return;
    }

    setActiveIndex((prev) => prev + 1);
  };

  if (!directions.length) {
    return null;
  }

  const turnClass =
    getTurnClass(current?.instruction);

  return (
    <div className="navigation-overlay">

      {/* ============================================
          TOP TURN CARD
      ============================================ */}

      <div
        className={`navigation-turn-card ${turnClass}`}
      >

        <div className="turn-icon-large">
          {TURN_ICON[current?.instruction] || "↑"}
        </div>

        <div className="turn-info">

          <div className="turn-distance">

            {distanceToTurn != null
              ? distanceToTurn < 5
                ? "Now"
                : formatDistance(distanceToTurn)
              : current?.distance_m > 0
              ? formatDistance(current.distance_m)
              : "Now"}

          </div>

          <div className="turn-instruction">
            {current?.instruction}
          </div>

          {next && (
            <div className="after-turn">
              Then {next.instruction.toLowerCase()}
            </div>
          )}

        </div>

        {/* VOICE BUTTON */}

        <button
          className={`voice-button ${
            voiceEnabled ? "active" : ""
          }`}
          onClick={() => {

            if (voiceEnabled) {
              setVoiceEnabled(false);
              window.speechSynthesis?.cancel();
            } else {
              setVoiceEnabled(true);

              setTimeout(() => {
                handleVoice();
              }, 50);
            }

          }}
          title="Voice navigation"
        >
          {voiceEnabled ? "🔊" : "🔇"}
        </button>

      </div>


      {/* ============================================
          BOTTOM INFO CARD
      ============================================ */}

      <div className="navigation-bottom-card">

        <div className="nav-stat">

          <span className="nav-stat-label">
            DISTANCE
          </span>

          <span className="nav-stat-value">
            {route?.distance_km
              ? `${Number(
                  route.distance_km
                ).toFixed(1)} km`
              : "--"}
          </span>

        </div>


        <div className="nav-divider" />


        <div className="nav-stat">

          <span className="nav-stat-label">
            STEPS
          </span>

          <span className="nav-stat-value">
            {activeIndex + 1}/
            {directions.length}
          </span>

        </div>


        <div className="nav-divider" />


        <div className="nav-next">

          <span className="nav-stat-label">
            NEXT
          </span>

          <span className="nav-next-text">
            {next
              ? `${TURN_ICON[next.instruction] || "↑"} ${
                  next.instruction
                }`
              : "Destination"}
          </span>

        </div>


        {/* GPS STATUS */}

        <div className="gps-status">

          <span
            className={`gps-dot ${
              gpsLocation
                ? "gps-active"
                : ""
            }`}
          />

          {gpsLocation
            ? "GPS Active"
            : "GPS waiting..."}

        </div>

      </div>


      {/* ============================================
          MANUAL NAVIGATION CONTROLS
      ============================================ */}

      <div className="navigation-controls">

        <button
          className="nav-control-button"
          onClick={handleBack}
          disabled={activeIndex === 0}
        >
          ← Back
        </button>


        <div className="nav-step-indicator">
          {activeIndex + 1} / {directions.length}
        </div>


        <button
          className="nav-control-button"
          onClick={handleNext}
          disabled={
            activeIndex >=
            directions.length - 1
          }
        >
          Next →
        </button>

      </div>

    </div>
  );
}