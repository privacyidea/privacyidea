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
  DOCUMENT,
  inject,
  Injectable,
  Renderer2,
  RendererFactory2,
  Signal,
  signal,
  WritableSignal
} from "@angular/core";
import { APP_APPEARANCE_COOKIE_NAME } from "@core/constants";
import { readCookie, writeCookie } from "@core/cookie";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  UserSettingKey,
  UserSettingsService,
  UserSettingsServiceInterface
} from "@services/user-settings/user-settings.service";

/**
 * How much depth the UI has: drives the drop shadows of raised surfaces and the recess
 * of sunken ones (the dashboard well, detail cards) together. At "flat" the raised
 * surfaces carry a hairline ring instead of a shadow and the recesses disappear.
 */
export const DEPTH_LEVELS = ["flat", "subtle", "default", "strong", "very-strong"] as const;
export type DepthLevel = (typeof DEPTH_LEVELS)[number];

/**
 * Stops of the light-source dial. Each level is its index as a string, and the angle it
 * stands for is index * LIGHT_SOURCE_STEP_ANGLE degrees, measured from due right and
 * growing clockwise. styles.scss generates one html.light-source-<index> block per stop
 * from a matching $light-source-steps -- keep the two counts in step.
 */
export const LIGHT_SOURCE_STEPS = 18;
export const LIGHT_SOURCE_STEP_ANGLE = 360 / LIGHT_SOURCE_STEPS;
export const LIGHT_SOURCE_LEVELS: readonly string[] = Array.from({ length: LIGHT_SOURCE_STEPS }, (_, index) =>
  String(index)
);
export type LightSourceLevel = string;

/** 17 * 20 = 340 degrees: light from just above the right. */
export const DEFAULT_LIGHT_SOURCE = "17";

/** The global corner radius. */
export const CORNER_LEVELS = ["square", "default", "round", "extra-round"] as const;
export type CornerLevel = (typeof CORNER_LEVELS)[number];

/** One group of mutually exclusive levels, and how it reaches the DOM and the store. */
interface LevelGroup<T extends string> {
  levels: readonly T[];
  fallback: T;
  classPrefix: string;
  settingKey: UserSettingKey;
  level: WritableSignal<T>;
}

/**
 * Owns the appearance the user picks in the UI settings: depth, light source and
 * corner radius.
 * Each group is applied as a class on the HTML element, which the
 * stylesheet turns into the matching design-token values -- the tokens themselves
 * stay theme-aware, so a level does not freeze a light-mode tone into dark mode.
 *
 * Mirrors ThemeService: the levels are cached in a cookie so the first paint after a
 * reload already carries them, and for an authenticated principal they are stored as
 * user settings, so they follow them to their other devices.
 */
@Injectable({
  providedIn: "root"
})
export class AppearanceService {
  private readonly rendererFactory = inject(RendererFactory2);
  private readonly htmlElement: HTMLHtmlElement = inject(DOCUMENT).documentElement as HTMLHtmlElement;
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly userSettingsService: UserSettingsServiceInterface = inject(UserSettingsService);
  private readonly renderer: Renderer2 = this.rendererFactory.createRenderer(null, null);

  private readonly depthGroup: LevelGroup<DepthLevel> = {
    levels: DEPTH_LEVELS,
    fallback: "default",
    classPrefix: "depth-",
    settingKey: "depth",
    level: signal<DepthLevel>("default")
  };
  private readonly lightSourceGroup: LevelGroup<LightSourceLevel> = {
    levels: LIGHT_SOURCE_LEVELS,
    fallback: DEFAULT_LIGHT_SOURCE,
    classPrefix: "light-source-",
    settingKey: "light_source",
    level: signal<LightSourceLevel>(DEFAULT_LIGHT_SOURCE)
  };
  private readonly cornerGroup: LevelGroup<CornerLevel> = {
    levels: CORNER_LEVELS,
    fallback: "default",
    classPrefix: "corner-",
    settingKey: "corner_radius",
    level: signal<CornerLevel>("default")
  };

  public readonly depth: Signal<DepthLevel> = this.depthGroup.level.asReadonly();
  public readonly lightSource: Signal<LightSourceLevel> = this.lightSourceGroup.level.asReadonly();
  public readonly corners: Signal<CornerLevel> = this.cornerGroup.level.asReadonly();

  /**
   * Applies the appearance cached in the browser. For an authenticated principal the
   * stored user settings are the authoritative source, but they only arrive after
   * login -- the cache keeps the login screen and the first paint from showing a
   * different appearance than the one the user picked.
   */
  public initializeAppearance(): void {
    const cached = this.readCachedAppearance();
    this.applyStoredDepth(cached["depth"]);
    this.applyStoredLightSource(cached["light_source"]);
    this.applyStoredCorners(cached["corner_radius"]);
  }

  public setDepth(level: DepthLevel): void {
    this.set(this.depthGroup, level);
  }

  public setLightSource(level: LightSourceLevel): void {
    this.set(this.lightSourceGroup, level);
  }

  public setCorners(level: CornerLevel): void {
    this.set(this.cornerGroup, level);
  }

  /**
   * Applies a level that is already stored (user setting or cookie) without writing it
   * back to the backend. An unknown value falls back to the default level.
   */
  public applyStoredDepth(level: unknown): void {
    this.apply(this.depthGroup, level);
  }

  public applyStoredLightSource(level: unknown): void {
    this.apply(this.lightSourceGroup, level);
  }

  public applyStoredCorners(level: unknown): void {
    this.apply(this.cornerGroup, level);
  }

  /** Puts every appearance group back on its default level, and stores that. */
  public resetToDefaults(): void {
    this.setDepth(this.depthGroup.fallback);
    this.setLightSource(this.lightSourceGroup.fallback);
    this.setCorners(this.cornerGroup.fallback);
  }

  private set<T extends string>(group: LevelGroup<T>, level: T): void {
    this.apply(group, level);
    if (this.authService.isAuthenticated()) {
      this.userSettingsService.setSetting(group.settingKey, group.level()).subscribe({ error: () => undefined });
    }
  }

  private apply<T extends string>(group: LevelGroup<T>, level: unknown): void {
    const applied = group.levels.includes(level as T) ? (level as T) : group.fallback;
    // Every level of the group goes first: leaving a stale class behind would let
    // declaration order in the stylesheet decide which level wins.
    group.levels.forEach((offered) => this.renderer.removeClass(this.htmlElement, `${group.classPrefix}${offered}`));
    this.renderer.addClass(this.htmlElement, `${group.classPrefix}${applied}`);
    group.level.set(applied);
    this.cacheAppearance();
  }

  private cacheAppearance(): void {
    writeCookie(
      APP_APPEARANCE_COOKIE_NAME,
      JSON.stringify({
        depth: this.depthGroup.level(),
        light_source: this.lightSourceGroup.level(),
        corner_radius: this.cornerGroup.level()
      })
    );
  }

  private readCachedAppearance(): Record<string, unknown> {
    const cached = readCookie(APP_APPEARANCE_COOKIE_NAME);
    if (cached === null) {
      return {};
    }
    try {
      const parsed: unknown = JSON.parse(cached);
      // A hand-edited or truncated cookie must not keep the app from starting: an
      // unusable cache is answered like an absent one, which applies the defaults.
      return typeof parsed === "object" && parsed !== null ? (parsed as Record<string, unknown>) : {};
    } catch {
      return {};
    }
  }
}
