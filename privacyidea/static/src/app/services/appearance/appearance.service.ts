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
import { Observable, catchError, of, shareReplay } from "rxjs";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  UserSettingKey,
  UserSettingsService,
  UserSettingsServiceInterface
} from "@services/user-settings/user-settings.service";

/**
 * How much depth the UI has: the drop shadows of raised surfaces and the recess of sunken ones
 * together. Every level needs its own html.depth-<level> block in styles/styles.scss.
 */
export const DEPTH_LEVELS = ["flat", "subtle", "default", "strong", "very-strong"] as const;
export type DepthLevel = (typeof DEPTH_LEVELS)[number];

/**
 * Stops of the light-source dial. A level is its index as a string; its angle is
 * index * LIGHT_SOURCE_STEP_ANGLE degrees, from due right and growing clockwise. The two purely
 * horizontal stops, 0 and 180 degrees, are left out. styles/styles.scss generates the matching
 * html.light-source-<index> blocks from $light-source-steps and skips the same two angles, so both
 * the count and the exclusions have to stay in step.
 */
export const LIGHT_SOURCE_STEPS = 18;
export const LIGHT_SOURCE_STEP_ANGLE = 360 / LIGHT_SOURCE_STEPS;
export const LIGHT_SOURCE_LEVELS: readonly string[] = Array.from({ length: LIGHT_SOURCE_STEPS }, (_, index) => index)
  .filter((index) => index * LIGHT_SOURCE_STEP_ANGLE !== 0 && index * LIGHT_SOURCE_STEP_ANGLE !== 180)
  .map(String);
export type LightSourceLevel = string;

/** 16 * 20 = 320 degrees: light from the upper right. */
export const DEFAULT_LIGHT_SOURCE = "16";

/** Levels of the global corner radius; the names are the $corner-radii keys in styles/styles.scss. */
export const CORNER_LEVELS = ["square", "default", "round", "extra-round"] as const;
export type CornerLevel = (typeof CORNER_LEVELS)[number];

/** One group of mutually exclusive levels, exactly one of which is a class on <html> at a time. */
interface LevelGroup<T extends string> {
  levels: readonly T[];
  fallback: T;
  classPrefix: string;
  settingKey: UserSettingKey;
  level: WritableSignal<T>;
}

/**
 * Owns the appearance the user picks in UI Settings: depth, light source and corner radius. Each
 * group is a class on the <html> element, which the stylesheet turns into design-token values. A
 * cookie caches the levels for the first paint; for an authenticated principal the stored user
 * settings are authoritative and override that cache once they arrive.
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

  /** Applies the cookie-cached levels at bootstrap, before any stored setting can arrive. */
  public initializeAppearance(): void {
    const cached = this.readCachedAppearance();
    this.apply(this.depthGroup, cached["depth"]);
    this.apply(this.lightSourceGroup, cached["light_source"]);
    this.apply(this.cornerGroup, cached["corner_radius"]);
    // One write for all three groups: caching per group would persist half-updated intermediate states.
    this.cacheAppearance();
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
   * Applies and stores depth, corners and light source together in one request, for callers
   * that change all three at once (e.g. an appearance preset) -- three separate setDepth /
   * setCorners / setLightSource calls would be three racing POSTs, and whichever response
   * lands last would overwrite the settings document with a stale value for the other two.
   */
  public setPreset(depth: DepthLevel, corner: CornerLevel, lightSource: LightSourceLevel): Observable<unknown> {
    this.apply(this.depthGroup, depth);
    this.apply(this.cornerGroup, corner);
    this.apply(this.lightSourceGroup, lightSource);
    const written$ = this.storeAll([this.depthGroup, this.cornerGroup, this.lightSourceGroup]);
    this.cacheAppearance();
    return written$;
  }

  /** Applies a stored level (user setting or cookie) without writing it back; unknown values fall back. */
  public applyStoredDepth(level: unknown): void {
    this.apply(this.depthGroup, level);
    this.cacheAppearance();
  }

  public applyStoredLightSource(level: unknown): void {
    this.apply(this.lightSourceGroup, level);
    this.cacheAppearance();
  }

  public applyStoredCorners(level: unknown): void {
    this.apply(this.cornerGroup, level);
    this.cacheAppearance();
  }

  /**
   * Resets every group to its default and reports once all three writes have settled, so a
   * caller that also navigates away (switching locale is a full-page load) can wait for them
   * first -- otherwise the navigation would abort them mid-flight and the reset would only
   * half stick.
   */
  public resetToDefaults(): Observable<unknown> {
    this.apply(this.depthGroup, this.depthGroup.fallback);
    this.apply(this.lightSourceGroup, this.lightSourceGroup.fallback);
    this.apply(this.cornerGroup, this.cornerGroup.fallback);
    const written$ = this.storeAll([this.depthGroup, this.lightSourceGroup, this.cornerGroup]);
    // One write for all three groups: caching per group would persist half-updated intermediate states.
    this.cacheAppearance();
    return written$;
  }

  private set<T extends string>(group: LevelGroup<T>, level: T): void {
    this.apply(group, level);
    this.store(group);
    this.cacheAppearance();
  }

  /**
   * Persists a group's current level for an authenticated principal; anonymous ones keep the
   * cookie only. Fires the write immediately regardless of whether the caller uses the returned
   * Observable -- shareReplay lets it also be awaited without triggering a second request, and
   * a failed write still resolves so waiting on it never hangs.
   */
  private store<T extends string>(group: LevelGroup<T>): Observable<unknown> {
    if (!this.authService.isAuthenticated()) {
      return of(null);
    }
    const write$ = this.userSettingsService.setSetting(group.settingKey, group.level()).pipe(
      catchError(() => of(null)),
      shareReplay(1)
    );
    write$.subscribe();
    return write$;
  }

  /**
   * Persists several groups' current levels in one request instead of one POST per group --
   * separate writes would race, and whichever response lands last would overwrite the settings
   * document with a stale value for the others. Same fire-immediately / shareReplay / never-hang
   * contract as store().
   */
  private storeAll(groups: LevelGroup<string>[]): Observable<unknown> {
    if (!this.authService.isAuthenticated()) {
      return of(null);
    }
    const values: Record<string, unknown> = {};
    groups.forEach((group) => (values[group.settingKey] = group.level()));
    const write$ = this.userSettingsService.setSettings(values).pipe(
      catchError(() => of(null)),
      shareReplay(1)
    );
    write$.subscribe();
    return write$;
  }

  private apply<T extends string>(group: LevelGroup<T>, level: unknown): void {
    const applied = group.levels.includes(level as T) ? (level as T) : group.fallback;
    // Remove all of them first: a stale class would let stylesheet order decide which level wins.
    group.levels.forEach((offered) => this.renderer.removeClass(this.htmlElement, `${group.classPrefix}${offered}`));
    this.renderer.addClass(this.htmlElement, `${group.classPrefix}${applied}`);
    group.level.set(applied);
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
      // A cookie that is not a JSON object reads as an absent one, so the fallback levels apply.
      return typeof parsed === "object" && parsed !== null ? (parsed as Record<string, unknown>) : {};
    } catch {
      return {};
    }
  }
}
