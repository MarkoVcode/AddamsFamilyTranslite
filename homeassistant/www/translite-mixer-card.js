// Translite mixer card: vertical faders for the Addams Family translite.
// One strip per Pi channel (with its on/play switch) plus the amplifier master.
// No dependencies. Install: see homeassistant/translite-dashboard.yaml.
//
//   type: custom:translite-mixer-card      # defaults match translite.yaml
//   title: Mixer                            # optional
//   channels:                               # optional, overrides the defaults
//     - entity: number.translite_music_volume
//       name: Addams
//       switch: switch.translite_addams_music
//       color: "#7e57c2"
//   master:
//     entity: number.translite_master_volume
//     name: Master
//     color: "#e53935"

const DEFAULTS = {
  title: "Mixer",
  channels: [
    { entity: "number.translite_music_volume", name: "Addams", icon: "mdi:hand-clap",
      switch: "switch.translite_addams_music", switchLabel: "PLAY", color: "#7e57c2" },
    { entity: "number.translite_radio_volume", name: "Radio", icon: "mdi:radio",
      switch: "switch.translite_radio", switchLabel: "ON", color: "#26a69a" },
  ],
  master: { entity: "number.translite_master_volume", name: "Master", icon: "mdi:volume-high", color: "#e53935" },
};

class TransliteMixerCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      title: config.title !== undefined ? config.title : DEFAULTS.title,
      channels: config.channels || DEFAULTS.channels,
      master: Object.assign({}, DEFAULTS.master, config.master || {}),
    };
    this._dragging = {};
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    this._update();
  }

  _strips() {
    return this._config.channels.map((c) => Object.assign({ master: false }, c))
      .concat([Object.assign({ master: true }, this._config.master)]);
  }

  _build() {
    const root = this.attachShadow ? (this.shadowRoot || this.attachShadow({ mode: "open" })) : this;
    const title = this._config.title ? `<div class="title">${this._config.title}</div>` : "";
    root.innerHTML = `
      <style>
        ha-card { padding: 16px 12px 12px; }
        .title { font-size: 1.15em; font-weight: 500; padding: 0 4px 12px; color: var(--primary-text-color); }
        .desk {
          display: flex; justify-content: center; gap: 10px;
          background: linear-gradient(180deg, rgba(127,127,127,.10), rgba(127,127,127,.03));
          border: 1px solid var(--divider-color, rgba(127,127,127,.25));
          border-radius: 14px; padding: 14px 10px 10px;
        }
        .strip {
          flex: 1 1 0; max-width: 92px; min-width: 64px;
          display: flex; flex-direction: column; align-items: center; gap: 8px;
          padding: 8px 4px; border-radius: 10px;
          background: var(--card-background-color, transparent);
          box-shadow: inset 0 0 0 1px var(--divider-color, rgba(127,127,127,.2));
        }
        .strip.master { margin-left: 8px; box-shadow: inset 0 0 0 2px var(--c); }
        .sep { width: 1px; background: var(--divider-color, rgba(127,127,127,.3)); margin: 6px 0; }
        .display {
          font-family: "Roboto Mono", ui-monospace, monospace; font-size: 1.05em; font-weight: 600;
          color: var(--c); background: #141414; border-radius: 6px;
          padding: 3px 0; width: 100%; text-align: center; letter-spacing: .5px;
          text-shadow: 0 0 6px var(--c);
        }
        .unit { font-size: .7em; opacity: .7; margin-left: 1px; }
        .track { position: relative; height: 190px; width: 44px; display: flex; justify-content: center; }
        .ticks {
          position: absolute; inset: 9px 0; pointer-events: none;
          background: repeating-linear-gradient(0deg, var(--secondary-text-color) 0 1px, transparent 1px 10%);
          opacity: .25; mask: linear-gradient(90deg, #000 0 22%, transparent 22% 78%, #000 78%);
          -webkit-mask: linear-gradient(90deg, #000 0 22%, transparent 22% 78%, #000 78%);
        }
        input[type=range] {
          writing-mode: vertical-lr; direction: rtl;
          -webkit-appearance: none; appearance: none;
          height: 100%; width: 44px; margin: 0; background: transparent; cursor: pointer;
        }
        input[type=range]::-webkit-slider-runnable-track {
          width: 8px; border-radius: 4px;
          background: linear-gradient(0deg, var(--c) 0 var(--p), rgba(127,127,127,.35) var(--p) 100%);
        }
        input[type=range]::-moz-range-track { width: 8px; border-radius: 4px; background: rgba(127,127,127,.35); }
        input[type=range]::-moz-range-progress { width: 8px; border-radius: 4px; background: var(--c); }
        input[type=range]::-webkit-slider-thumb {
          -webkit-appearance: none; width: 38px; height: 18px; margin-left: -15px; border-radius: 4px;
          background: linear-gradient(180deg, #f5f5f5, #9e9e9e 45%, #424242 50%, #9e9e9e 55%, #e0e0e0);
          box-shadow: 0 2px 4px rgba(0,0,0,.5);
        }
        input[type=range]::-moz-range-thumb {
          width: 38px; height: 18px; border: 0; border-radius: 4px;
          background: linear-gradient(180deg, #f5f5f5, #9e9e9e 45%, #424242 50%, #9e9e9e 55%, #e0e0e0);
          box-shadow: 0 2px 4px rgba(0,0,0,.5);
        }
        input[type=range]:disabled { cursor: not-allowed; opacity: .35; }
        .name { display: flex; align-items: center; gap: 4px; font-size: .85em; font-weight: 500;
                color: var(--primary-text-color); white-space: nowrap; }
        .name ha-icon { --mdc-icon-size: 16px; color: var(--c); }
        button {
          width: 100%; border: 0; border-radius: 6px; padding: 6px 0; cursor: pointer;
          font-weight: 700; font-size: .75em; letter-spacing: 1px;
          background: rgba(127,127,127,.18); color: var(--secondary-text-color);
          transition: background .2s, box-shadow .2s, color .2s;
        }
        button.on { background: var(--c); color: #fff; box-shadow: 0 0 10px var(--c); }
        button:disabled { opacity: .35; cursor: not-allowed; }
        .spacer { height: 27px; }
      </style>
      <ha-card>${title}<div class="desk"></div></ha-card>`;
    const desk = root.querySelector(".desk");
    this._els = {};
    this._strips().forEach((s) => {
      if (s.master) {
        const sep = document.createElement("div");
        sep.className = "sep";
        desk.appendChild(sep);
      }
      const el = document.createElement("div");
      el.className = "strip" + (s.master ? " master" : "");
      el.style.setProperty("--c", s.color || "var(--primary-color)");
      el.innerHTML = `
        <div class="display">--</div>
        <div class="track"><div class="ticks"></div><input type="range"></div>
        <div class="name">${s.icon ? `<ha-icon icon="${s.icon}"></ha-icon>` : ""}${s.name || ""}</div>
        ${s.switch ? `<button>${s.switchLabel || "ON"}</button>` : `<div class="spacer"></div>`}`;
      const slider = el.querySelector("input");
      slider.addEventListener("input", () => {
        this._dragging[s.entity] = true;
        this._show(s, el, Number(slider.value));
      });
      // send once on release, so a drag is one MQTT message
      slider.addEventListener("change", () => {
        this._hass.callService("number", "set_value", { entity_id: s.entity, value: Number(slider.value) });
        setTimeout(() => { this._dragging[s.entity] = false; }, 1500);
      });
      const button = el.querySelector("button");
      if (button) {
        button.addEventListener("click", () => {
          this._hass.callService("switch", "toggle", { entity_id: s.switch });
        });
      }
      desk.appendChild(el);
      this._els[s.entity] = { el, slider, button, strip: s };
    });
    this._built = true;
  }

  _show(s, el, value) {
    const st = this._hass.states[s.entity];
    const min = st ? Number(st.attributes.min) : 0;
    const max = st ? Number(st.attributes.max) : 100;
    const unit = st && st.attributes.unit_of_measurement ? st.attributes.unit_of_measurement : "";
    el.querySelector(".display").innerHTML = `${Math.round(value)}<span class="unit">${unit}</span>`;
    el.querySelector("input").style.setProperty("--p", ((value - min) / (max - min || 1) * 100) + "%");
  }

  _update() {
    Object.values(this._els).forEach(({ el, slider, button, strip }) => {
      const st = this._hass.states[strip.entity];
      const ok = st && !["unavailable", "unknown"].includes(st.state);
      slider.disabled = !ok;
      if (st) {
        slider.min = st.attributes.min;
        slider.max = st.attributes.max;
        slider.step = st.attributes.step || 1;
      }
      if (!ok) {
        el.querySelector(".display").textContent = "--";
      } else if (!this._dragging[strip.entity]) {
        slider.value = st.state;
        this._show(strip, el, Number(st.state));
      }
      if (button) {
        const sw = this._hass.states[strip.switch];
        button.classList.toggle("on", !!sw && sw.state === "on");
        button.disabled = !sw || ["unavailable", "unknown"].includes(sw.state);
      }
    });
  }

  getCardSize() { return 6; }
  getGridOptions() { return { columns: 12, rows: 6, min_columns: 6 }; }
  static getStubConfig() { return {}; }
}

customElements.define("translite-mixer-card", TransliteMixerCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "translite-mixer-card",
  name: "Translite mixer",
  description: "Vertical faders: Addams music, radio and amplifier master",
});
