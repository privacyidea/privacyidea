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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";

import { ConditionalAccessCell } from "./conditional-access-cell";

describe("ConditionalAccessCell", () => {
  let component: ConditionalAccessCell;
  let fixture: ComponentFixture<ConditionalAccessCell>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessCell],
      // The policy link is a routerLink, which needs an ActivatedRoute.
      providers: [provideRouter([])]
    }).compileComponents();
    fixture = TestBed.createComponent(ConditionalAccessCell);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("entryId", 42);
    // The policies these tests link to, with the id each has *now*. An outcome stores only the policy's name, so this
    // map is what makes a link possible - and only for a name that still exists (see the deleted-policy test).
    fixture.componentRef.setInput(
      "policyIdsByName",
      new Map([
        ["Brute Force PIN Lockout", 7],
        ["Permanent IP Block", 7],
        ["Email Notification Test", 3],
        ["Notify", 3],
        ["Brute force", 7]
      ])
    );
  });

  function viewsFor(outcomes: unknown) {
    fixture.componentRef.setInput("outcomes", outcomes);
    return component.views();
  }

  it("shows what a dry-run policy would have done, marked as unenforced", () => {
    expect(
      viewsFor([
        {
          id: 12,
          auth_log_id: 1,
          action_type: "LOCK_USER_TEMPORARY",
          dry_run: true,
          policy_name: "Brute Force PIN Lockout",
          threshold: 5,
          event_count: 5,
          stage_name: "Lock 10 min",
          info: { expires_at: "2026-08-03T09:10:00+00:00" }
        }
      ])
    ).toEqual([
      {
        key: "12",
        policy: "Brute Force PIN Lockout",
        policyLink: `${ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_DETAILS}7`,
        dryRun: true,
        action: "LOCK_USER_TEMPORARY",
        stage: "Lock 10 min",
        threshold: 5,
        expiresAt: "2026-08-03T09:10:00+00:00"
      }
    ]);
  });

  it("keeps only the fields the column shows, whatever else the row carries", () => {
    // An allow-list, so a new column on conditional_access_outcome cannot appear in the log column by accident.
    const [view] = viewsFor([
      { action_type: "EMAIL_ADMIN", policy_name: "Notify", dry_run: false, something_new: "leaked?" }
    ]);
    expect(Object.keys(view).sort()).toEqual([
      "action",
      "dryRun",
      "expiresAt",
      "key",
      "policy",
      "policyLink",
      "stage",
      "threshold"
    ]);
    expect(view.dryRun).toBe(false);
    expect(view.stage).toBeUndefined();
  });

  it("describes every outcome of the request, in order", () => {
    const views = viewsFor([
      { policy_name: "Permanent IP Block", action_type: "BLOCK_IP_PERMANENT", dry_run: true },
      { policy_name: "Email Notification Test", action_type: "EMAIL_ADMIN", dry_run: true }
    ]);
    expect(views.map((view) => view.policy)).toEqual(["Permanent IP Block", "Email Notification Test"]);
    expect(views.map((view) => view.action)).toEqual(["BLOCK_IP_PERMANENT", "EMAIL_ADMIN"]);
    expect(views.map((view) => view.policyLink)).toEqual([
      `${ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_DETAILS}7`,
      `${ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_DETAILS}3`
    ]);
  });

  it("identifies an unnamed stage by its threshold", () => {
    // stage_name is the one nullable identifier of a stage, so the threshold has to be shown: it is what an admin
    // recognizes the stage by when they never named one.
    const [view] = viewsFor([
      { policy_name: "Brute Force PIN Lockout", action_type: "LOCK_USER_TEMPORARY", threshold: 5, dry_run: false }
    ]);
    expect(view.threshold).toBe(5);
    expect(view.stage).toBeUndefined();
  });

  it("takes the expiry out of info, and only a usable one", () => {
    // Shown in the details, because once the lockout/block state row has lapsed this is the only record of how long the
    // restriction lasted. It is validated here and not in the template: `info` is free-form JSON and the date pipe
    // throws on a value it cannot parse.
    const views = viewsFor([
      { action_type: "LOCK_USER_TEMPORARY", info: { expires_at: "2026-08-03T09:10:00+00:00" } },
      // A permanent action has no expiry, an email restricts nothing, and neither garbage nor a non-dict `info` may
      // reach the pipe.
      { action_type: "LOCK_USER_PERMANENT", info: null },
      { action_type: "EMAIL_ADMIN" },
      { action_type: "LOCK_USER_TEMPORARY", info: { expires_at: "not a date" } },
      { action_type: "LOCK_USER_TEMPORARY", info: "" }
    ]);
    expect(views.map((view) => view.expiresAt)).toEqual([
      "2026-08-03T09:10:00+00:00",
      undefined,
      undefined,
      undefined,
      undefined
    ]);
  });

  it("keys an outcome by its row id, and by entry and position when it has none", () => {
    // The key addresses one outcome's details: it is what the expand toggle records and what its aria-controls points
    // at, so two outcomes of one cell must never share it.
    const views = viewsFor([{ id: 12, action_type: "LOCK_USER_TEMPORARY" }, { action_type: "EMAIL_ADMIN" }]);
    expect(views.map((view) => view.key)).toEqual(["12", "42-1"]);
  });

  it("omits the policy link when no policy of that name exists any more", () => {
    // The outcome names its policy and stores no id, precisely because a deleted policy's id can be handed to another
    // one. So a link is a lookup: no policy of that name, no link - and the denormalized name still reads.
    const [view] = viewsFor([{ policy_name: "Deleted policy", action_type: "LOCK_USER_TEMPORARY", dry_run: true }]);
    expect(view.policy).toBe("Deleted policy");
    expect(view.policyLink).toBeUndefined();
    expect(view.dryRun).toBe(true);
  });

  it("omits every policy link for an admin who may not read the policies", () => {
    // Then the caller passes no policies at all, so the column degrades to names without links rather than to links
    // that land on a page the admin cannot open.
    fixture.componentRef.setInput("policyIdsByName", new Map<string, number>());
    const [view] = viewsFor([{ policy_name: "Brute force", action_type: "LOCK_USER_TEMPORARY" }]);
    expect(view.policy).toBe("Brute force");
    expect(view.policyLink).toBeUndefined();
  });

  it("is empty for a request conditional access did nothing to, and for anything that is not a list", () => {
    // The table's skeleton rows set every column to "", which the nullish default does not catch - a list column must
    // render nothing there instead of throwing.
    expect(viewsFor([])).toEqual([]);
    expect(viewsFor(null)).toEqual([]);
    expect(viewsFor("")).toEqual([]);
    expect(viewsFor({ action_type: "LOCK_USER_TEMPORARY" })).toEqual([]);
  });

  it("starts collapsed and toggles one outcome at a time", () => {
    expect(component.isExpanded("12")).toBe(false);
    component.toggle("12");
    expect(component.isExpanded("12")).toBe(true);
    // Independent of each other: expanding one outcome must not open its neighbours.
    expect(component.isExpanded("13")).toBe(false);
    component.toggle("12");
    expect(component.isExpanded("12")).toBe(false);
  });

  it("collapses again when the cell is handed different outcomes", () => {
    // A table row is reused as pages change, so the keys of the outcomes that are gone say nothing about the new ones.
    fixture.componentRef.setInput("outcomes", [{ id: 12, action_type: "LOCK_USER_TEMPORARY" }]);
    component.toggle("12");
    expect(component.isExpanded("12")).toBe(true);

    fixture.componentRef.setInput("outcomes", [{ id: 99, action_type: "BLOCK_IP" }]);
    expect(component.isExpanded("12")).toBe(false);
  });

  it("names the expand toggle after the policy it belongs to, in both states", () => {
    // One button per outcome and no visible text on it, so the accessible name has to say which outcome it opens.
    const [view] = viewsFor([{ id: 12, policy_name: "Brute Force PIN Lockout", action_type: "LOCK_USER_TEMPORARY" }]);
    expect(component.toggleLabel(view)).toBe("Show the details of Brute Force PIN Lockout");
    component.toggle(view.key);
    expect(component.toggleLabel(view)).toBe("Hide the details of Brute Force PIN Lockout");
  });

  it("renders one line per outcome and reveals the rest only on the toggle", () => {
    fixture.componentRef.setInput("outcomes", [
      {
        id: 12,
        action_type: "LOCK_USER_TEMPORARY",
        dry_run: false,
        policy_name: "Brute Force PIN Lockout",
        threshold: 5,
        event_count: 5,
        stage_name: "Lock 10 min",
        info: { expires_at: "2026-06-22T10:10:00+00:00" }
      }
    ]);
    fixture.detectChanges();

    const toggle: HTMLButtonElement = fixture.nativeElement.querySelector("button.outcome-toggle");
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(toggle.getAttribute("aria-controls")).toBe("ca-outcome-12");
    // Collapsed, the cell names the policy that acted and nothing else.
    expect(fixture.nativeElement.textContent).toContain("Brute Force PIN Lockout");
    expect(fixture.nativeElement.textContent).not.toContain("LOCK_USER_TEMPORARY");
    expect(fixture.nativeElement.querySelector("a")?.getAttribute("href")).toContain(
      ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_DETAILS
    );

    toggle.click();
    fixture.detectChanges();
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    const details: HTMLElement = fixture.nativeElement.querySelector("#ca-outcome-12");
    expect(details.textContent).toContain("LOCK_USER_TEMPORARY");
    expect(details.textContent).toContain("Lock 10 min");
    expect(details.textContent).toContain("5");
  });
});
