import React from "react";

function ScoreCard({ title, score }) {
  return (
    <div className="score-card">
      <strong>{title}</strong>
      <p>{score}</p>
    </div>
  );
}

export default ScoreCard;
