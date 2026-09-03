/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import {
  currentSubPath,
  localeSegmentFromPath,
  localeTargetUrl,
  SCRIPT_ROOT_META_NAME,
  scriptRoot
} from "@core/locale";

function setPath(path: string): void {
  window.history.pushState(null, "", path);
}

function setScriptRoot(root: string | undefined): void {
  document.querySelector(`meta[name="${SCRIPT_ROOT_META_NAME}"]`)?.remove();
  if (root !== undefined) {
    const meta = document.createElement("meta");
    meta.setAttribute("name", SCRIPT_ROOT_META_NAME);
    meta.setAttribute("content", root);
    document.head.appendChild(meta);
  }
}

describe("scriptRoot", () => {
  afterEach(() => setScriptRoot(undefined));

  it("returns an empty string when the backend passed no mount prefix", () => {
    expect(scriptRoot()).toBe("");
  });

  it("returns the value from the meta tag for a sub-path mount", () => {
    setScriptRoot("/pi");
    expect(scriptRoot()).toBe("/pi");
  });

  it("returns an empty string for a root mount, where the meta tag is present but empty", () => {
    setScriptRoot("");
    expect(scriptRoot()).toBe("");
  });
});

describe("localeSegmentFromPath with a sub-path mount", () => {
  afterEach(() => setScriptRoot(undefined));

  it("strips the script root before matching the locale segment", () => {
    setScriptRoot("/pi");
    setPath("/pi/app/v2/de/tokens");
    expect(localeSegmentFromPath()).toBe("de");
  });

  it("returns null for an unknown locale segment, even under a sub-path mount", () => {
    setScriptRoot("/pi");
    setPath("/pi/app/v2/not-a-locale/");
    expect(localeSegmentFromPath()).toBeNull();
  });

  it("still works with no script root (mounted at the server root)", () => {
    setPath("/app/v2/de/");
    expect(localeSegmentFromPath()).toBe("de");
  });
});

describe("currentSubPath with a sub-path mount", () => {
  afterEach(() => setScriptRoot(undefined));

  it("returns the in-app route after the script root, /app/v2/ and the locale segment", () => {
    setScriptRoot("/pi");
    setPath("/pi/app/v2/de/tokens/list");
    expect(currentSubPath()).toBe("tokens/list");
  });

  it("still works with no script root", () => {
    setPath("/app/v2/de/tokens/list");
    expect(currentSubPath()).toBe("tokens/list");
  });
});

describe("localeTargetUrl with a sub-path mount", () => {
  afterEach(() => setScriptRoot(undefined));

  it("prepends the script root so switching languages keeps the sub-path mount", () => {
    setScriptRoot("/pi");
    setPath("/pi/app/v2/de/tokens");
    expect(localeTargetUrl("fr")).toBe("/pi/app/v2/fr/tokens");
  });

  it("does not prepend anything when mounted at the server root", () => {
    setPath("/app/v2/de/tokens");
    expect(localeTargetUrl("fr")).toBe("/app/v2/fr/tokens");
  });
});
