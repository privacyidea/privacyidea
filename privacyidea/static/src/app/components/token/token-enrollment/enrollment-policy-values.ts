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
import { HttpErrorResponse } from "@angular/common/http";
import { PiResponse } from "@app/app.component";
import { EnrollmentPolicies, EnrollmentPolicyState } from "@services/token/token.service";
import { Observable, catchError, map, of, startWith } from "rxjs";

export type TwoStepMode = "allow" | "force" | "disabled";

/** The progress of loading the enrollment policies of one target. */
export type EnrollmentPoliciesLoad =
  | { status: "idle" }
  | { status: "loading"; previous?: EnrollmentPolicies }
  | { status: "loaded"; policies: EnrollmentPolicies }
  | { status: "error"; message: string };

/** Turns a policy request into its load progress, starting with "loading" and ending in "loaded" or "error". */
export function loadEnrollmentPolicies(
  request: Observable<PiResponse<EnrollmentPolicies>>,
  previous?: EnrollmentPolicies
): Observable<EnrollmentPoliciesLoad> {
  return request.pipe(
    map((response): EnrollmentPoliciesLoad => {
      const policies = response.result?.value;
      return policies
        ? { status: "loaded", policies }
        : {
            status: "error",
            message:
              response.result?.error?.message ||
              $localize`:@@token.enrollmentPoliciesUnavailable:The enrollment policies could not be determined.`
          };
    }),
    catchError((error: HttpErrorResponse) =>
      of<EnrollmentPoliciesLoad>({
        status: "error",
        message: error.error?.result?.error?.message || error.message
      })
    ),
    startWith<EnrollmentPoliciesLoad>({ status: "loading", previous })
  );
}

/** The policy state the enrollment forms read: unrestricted without a target, pending while loading or failed. */
export function enrollmentPolicyState(load: EnrollmentPoliciesLoad): EnrollmentPolicyState {
  switch (load.status) {
    case "loaded":
      return { state: "loaded", policies: load.policies };
    case "idle":
      return { state: "unrestricted" };
    case "loading":
      return { state: "pending", previous: load.previous };
    default:
      return { state: "pending" };
  }
}

/** The enrollment policies to show, the previous ones while the next load, null where the target has none. */
export function loadedEnrollmentPolicies(state: EnrollmentPolicyState): EnrollmentPolicies | null {
  switch (state.state) {
    case "loaded":
      return state.policies;
    case "pending":
      return state.previous ?? null;
    default:
      return null;
  }
}

/** The two-step mode of the enrollment form: "allow" without a policy target (container template editor), else the policy's. */
export function twoStepMode(state: EnrollmentPolicyState): TwoStepMode {
  if (state.state === "unrestricted") {
    return "allow";
  }
  return loadedEnrollmentPolicies(state)?.["2step"] ?? "disabled";
}

/** A numeric policy value, undefined if it is not set or not a number. */
export function numericPolicyValue(value: string | undefined): number | undefined {
  const parsed = parseInt(value ?? "", 10);
  return isNaN(parsed) ? undefined : parsed;
}

/** The value an enrollment field starts with and whether a policy sets it, which locks the field. */
export interface FieldPreset<T> {
  value: T;
  locked: boolean;
}

/**
 * The value of an enrollment field after its preset changed, for example when the system config loads after the
 * dialog opened. A policy value always wins and locks the field. Otherwise a value the user picked is kept, `chosen`
 * also keeps a pick that equals the old preset. The caller drops `chosen` when the fields are reset or a policy locks
 * the field. A pick made before a lock is not restored, the field then shows the preset again.
 */
export function presetOrChoice<T>(
  preset: FieldPreset<T>,
  previous: { source: FieldPreset<T>; value: T } | undefined,
  chosen: boolean
): T {
  if (preset.locked || !previous) {
    return preset.value;
  }
  return previous.value !== previous.source.value || chosen ? previous.value : preset.value;
}

/** Compares two field presets by value, so that an equal preset does not reset the field. */
export function samePreset<T>(a: FieldPreset<T>, b: FieldPreset<T>): boolean {
  return a.value === b.value && a.locked === b.locked;
}

/** Compares two lists as sets, so that the same entries in another order do not count as a change. */
export function sameEntries<T>(a: readonly T[], b: readonly T[]): boolean {
  const setA = new Set(a);
  const setB = new Set(b);
  return setA.size === setB.size && [...setA].every((entry) => setB.has(entry));
}
