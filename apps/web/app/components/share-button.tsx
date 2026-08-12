"use client";

import { useState } from "react";

export default function ShareButton() {
  const [label, setLabel] = useState("Copy link");

  async function share() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setLabel("Link copied");
      window.setTimeout(() => setLabel("Copy link"), 1800);
    } catch {
      setLabel("Copy failed");
      window.setTimeout(() => setLabel("Copy link"), 1800);
    }
  }

  return <button className="quiet-button" type="button" onClick={share}>{label}</button>;
}

