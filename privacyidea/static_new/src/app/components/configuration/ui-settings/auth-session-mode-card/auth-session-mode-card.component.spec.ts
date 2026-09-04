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
import { Type } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatSelect, MatSelectChange } from "@angular/material/select";
import { AuthSessionMode, AuthSessionModeService } from "@services/auth-session-mode/auth-session-mode.service";
import { DialogService } from "@services/dialog/dialog.service";
import { MockAuthSessionModeService } from "@testing/mock-services/mock-auth-session-mode-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { AuthSessionModeCardComponent } from "./auth-session-mode-card.component";

interface CardInternals {
  modeOptions: () => { value: AuthSessionMode; label: string }[];
  modeHint: () => string;
  selectAuthSessionMode: (event: MatSelectChange) => Promise<void>;
}

describe("AuthSessionModeCardComponent", () => {
  let fixture: ComponentFixture<AuthSessionModeCardComponent>;
  let card: CardInternals;
  let modeService: MockAuthSessionModeService;
  let dialogService: MockDialogService;

  function selectionOf(value: AuthSessionMode): { event: MatSelectChange; source: { value: unknown } } {
    const source = { value } as unknown as MatSelect;
    return { event: { source, value } as MatSelectChange, source: source as unknown as { value: unknown } };
  }

  function build(): void {
    TestBed.resetTestingModule();
    modeService = new MockAuthSessionModeService();
    dialogService = new MockDialogService();
    TestBed.configureTestingModule({
      imports: [AuthSessionModeCardComponent],
      providers: [
        { provide: AuthSessionModeService as Type<unknown>, useValue: modeService },
        { provide: DialogService as Type<unknown>, useValue: dialogService }
      ]
    });
    fixture = TestBed.createComponent(AuthSessionModeCardComponent);
    card = fixture.componentInstance as unknown as CardInternals;
    fixture.detectChanges();
  }

  beforeEach(() => {
    (globalThis as { BroadcastChannel?: unknown }).BroadcastChannel = class {
      addEventListener = jest.fn();
      postMessage = jest.fn();
    };
    build();
  });

  afterEach(() => {
    delete (globalThis as { BroadcastChannel?: unknown }).BroadcastChannel;
  });

  describe("offered options", () => {
    it("offers all three modes where cross-tab sync works", () => {
      expect(card.modeOptions().map((option) => option.value)).toEqual([
        "single-tab",
        "multi-tab-ephemeral",
        "multi-tab-persistent"
      ]);
    });

    it("hides multi-tab-ephemeral without BroadcastChannel", () => {
      delete (globalThis as { BroadcastChannel?: unknown }).BroadcastChannel;
      build();
      expect(card.modeOptions().map((option) => option.value)).toEqual(["single-tab", "multi-tab-persistent"]);
    });

    it("still shows multi-tab-ephemeral while it is the active mode", () => {
      delete (globalThis as { BroadcastChannel?: unknown }).BroadcastChannel;
      build();
      modeService.mode.set("multi-tab-ephemeral");
      expect(card.modeOptions().map((option) => option.value)).toContain("multi-tab-ephemeral");
    });

    it("labels every option", () => {
      card.modeOptions().forEach((option) => expect(option.label.length).toBeGreaterThan(0));
    });
  });

  it("describes the active mode", () => {
    modeService.mode.set("multi-tab-persistent");
    const persistentHint = card.modeHint();
    modeService.mode.set("single-tab");
    expect(card.modeHint()).not.toBe(persistentHint);
  });

  describe("changing the mode", () => {
    it("applies a narrower mode without asking", async () => {
      modeService.mode.set("multi-tab-persistent");
      await card.selectAuthSessionMode(selectionOf("single-tab").event);
      expect(dialogService.openDialogAsync).not.toHaveBeenCalled();
      expect(modeService.setMode).toHaveBeenCalledWith("single-tab");
    });

    it("asks before widening the mode", async () => {
      modeService.mode.set("single-tab");
      await card.selectAuthSessionMode(selectionOf("multi-tab-persistent").event);
      expect(dialogService.openDialogAsync).toHaveBeenCalled();
      expect(modeService.setMode).toHaveBeenCalledWith("multi-tab-persistent");
    });

    it("keeps the current mode when the dialog is dismissed", async () => {
      modeService.mode.set("single-tab");
      dialogService.openDialogAsync.mockResolvedValue(undefined);
      const { event, source } = selectionOf("multi-tab-persistent");
      await card.selectAuthSessionMode(event);
      expect(modeService.setMode).not.toHaveBeenCalled();
      expect(source.value).toBe("single-tab");
    });

    it("asks again when stepping from ephemeral up to persistent", async () => {
      modeService.mode.set("multi-tab-ephemeral");
      await card.selectAuthSessionMode(selectionOf("multi-tab-persistent").event);
      expect(dialogService.openDialogAsync).toHaveBeenCalled();
    });

    it("does not ask when stepping from persistent down to ephemeral", async () => {
      modeService.mode.set("multi-tab-persistent");
      await card.selectAuthSessionMode(selectionOf("multi-tab-ephemeral").event);
      expect(dialogService.openDialogAsync).not.toHaveBeenCalled();
      expect(modeService.setMode).toHaveBeenCalledWith("multi-tab-ephemeral");
    });
  });
});
