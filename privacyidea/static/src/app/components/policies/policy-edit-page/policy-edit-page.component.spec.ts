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
import { Component, input, output, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { By } from "@angular/platform-browser";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { PolicyEditPageComponent } from "@components/policies/policy-edit-page/policy-edit-page.component";
import { PolicyActionSearchComponent } from "@components/policies/policy-edit-page/policy-action-search/policy-action-search.component";
import { PolicyTab } from "@components/policies/policy-edit-page/policy-panels/policy-panel-edit/policy-panel-edit.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import {
  MockContentService,
  MockNotificationService,
  MockPendingChangesService,
  MockPiResponse,
  MockPolicyService
} from "@testing/mock-services";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { of } from "rxjs";

@Component({ selector: "app-policy-panel-edit", standalone: true, template: "" })
class MockPanel {
  policy = input.required<PolicyDetail>();
  activeTab = input<PolicyTab>("actions");
  actionFilter = input<string>("");
  searchInHeader = input<boolean>(false);
  policyEdit = output<Partial<PolicyDetail>>();
  activeTabChange = output<PolicyTab>();
  actionFilterChange = output<string>();
  searchAnchor = signal<HTMLElement | undefined>(undefined);
  searchField = signal<Partial<PolicyActionSearchComponent> | undefined>(undefined);
}

function createTestBed(paramName: string | null) {
  return TestBed.configureTestingModule({
    imports: [PolicyEditPageComponent],
    providers: [
      {
        provide: ActivatedRoute,
        useValue: { paramMap: of({ get: (key: string) => (key === "name" ? paramName : null) }) }
      },
      {
        provide: Router,
        useValue: { navigateByUrl: jest.fn(), events: of(), url: ROUTE_PATHS.POLICIES }
      },
      { provide: PolicyService, useClass: MockPolicyService },
      { provide: ContentService, useClass: MockContentService },
      { provide: DialogService, useClass: MockDialogService },
      { provide: PendingChangesService, useClass: MockPendingChangesService },
      { provide: NotificationService, useClass: MockNotificationService }
    ]
  })
    .overrideComponent(PolicyEditPageComponent, {
      set: {
        imports: [
          MockPanel,
          MatButtonModule,
          MatIconModule,
          PolicyActionSearchComponent,
          StickyHeaderDirective,
          ScrollToTopDirective
        ]
      }
    })
    .compileComponents();
}

describe("PolicyEditPageComponent – create mode", () => {
  let component: PolicyEditPageComponent;
  let fixture: ComponentFixture<PolicyEditPageComponent>;
  let policyService: MockPolicyService;
  let dialogService: MockDialogService;
  let router: Router;

  beforeEach(async () => {
    await createTestBed(null);

    fixture = TestBed.createComponent(PolicyEditPageComponent);
    component = fixture.componentInstance;
    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should be in create mode when no name param", () => {
    expect(component.mode()).toBe("create");
  });

  it("should merge edits into the policy", () => {
    component.addPolicyEdit({ priority: 99 });
    expect(component.editedPolicy().priority).toBe(99);
  });

  it("canSave returns false if no edits", () => {
    expect(component.canSave()).toBe(false);
  });

  it("canSave returns false if name is missing", () => {
    component.addPolicyEdit({ name: "" });
    expect(component.canSave()).toBe(false);
  });

  it("canSave returns true if edits and name present", () => {
    // TODO: Not only name, but also scope and at least one action should be required
    component.addPolicyEdit({ name: "ValidName" });
    expect(component.canSave()).toBe(true);
  });

  const mockPanel = (): MockPanel => fixture.debugElement.query(By.directive(MockPanel)).componentInstance;

  function scrollSearchAnchorTo(anchorTop: number) {
    const header: HTMLElement = fixture.debugElement.query(By.directive(StickyHeaderDirective)).nativeElement;
    jest.spyOn(header, "getBoundingClientRect").mockReturnValue({ bottom: 100 } as DOMRect);
    const anchor = document.createElement("div");
    jest.spyOn(anchor, "getBoundingClientRect").mockReturnValue({ top: anchorTop } as DOMRect);
    mockPanel().searchAnchor.set(anchor);

    fixture.debugElement.query(By.directive(ScrollToTopDirective)).nativeElement.dispatchEvent(new Event("scroll"));
    fixture.detectChanges();
  }

  const headerSearchField = () => fixture.debugElement.query(By.directive(PolicyActionSearchComponent));

  it("keeps the action search out of the header until the header reaches it", () => {
    scrollSearchAnchorTo(101);

    expect(headerSearchField()).toBeNull();
  });

  it("takes the action search into the header once the header touches its top edge", () => {
    scrollSearchAnchorTo(100);

    expect(headerSearchField()).not.toBeNull();
  });

  it("gives the action search back to the tab when scrolled up again", () => {
    scrollSearchAnchorTo(40);
    scrollSearchAnchorTo(140);

    expect(headerSearchField()).toBeNull();
  });

  it("keeps the action search out of the header on the conditions tab", () => {
    component.activeTab.set("conditions");
    scrollSearchAnchorTo(40);

    expect(headerSearchField()).toBeNull();
  });

  describe("focus handoff", () => {
    const headerSearchInput = (): HTMLInputElement => headerSearchField().query(By.css("input")).nativeElement;

    beforeEach(() => {
      component.actionFilter.set("token");
    });

    it("moves focus and caret into the header copy when the field moves up", async () => {
      mockPanel().searchField.set({ focusedSelection: () => ({ start: 1, end: 3 }) });

      scrollSearchAnchorTo(100);
      await fixture.whenStable();

      const input = headerSearchInput();
      expect(document.activeElement).toBe(input);
      expect([input.selectionStart, input.selectionEnd]).toEqual([1, 3]);
    });

    it("moves focus and caret back to the tab copy when the field returns", async () => {
      const takeFocus = jest.fn();
      mockPanel().searchField.set({ focusedSelection: () => null, takeFocus });
      scrollSearchAnchorTo(100);
      headerSearchInput().focus();
      headerSearchInput().setSelectionRange(2, 4);

      scrollSearchAnchorTo(140);
      await fixture.whenStable();

      expect(takeFocus).toHaveBeenCalledWith({ start: 2, end: 4 });
    });

    it("leaves focus alone when the search field does not have it", async () => {
      mockPanel().searchField.set({ focusedSelection: () => null });

      scrollSearchAnchorTo(100);
      await fixture.whenStable();

      expect(document.activeElement).not.toBe(headerSearchInput());
    });
  });

  it("onAction does not call onSave if value is not submit", () => {
    const spy = jest.spyOn(component, "onSave");
    component.onAction(null);
    expect(spy).not.toHaveBeenCalled();
  });

  it("onAction calls onSave if value is submit", () => {
    const spy = jest.spyOn(component, "onSave");
    component.onAction("submit");
    expect(spy).toHaveBeenCalled();
  });

  it("onCancel navigates back directly when no changes", () => {
    component.onCancel();
    expect(dialogService.openDialog).not.toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES);
  });

  it("savePolicy calls saveNewPolicy in create mode and navigates back", async () => {
    const spy = jest.spyOn(policyService, "saveNewPolicy").mockResolvedValue(true);
    const success = await component.onSave();
    expect(spy).toHaveBeenCalled();
    expect(success).toBe(true);
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES);
  });

  it("savePolicy does not navigate when saveNewPolicy returns false", async () => {
    jest.spyOn(policyService, "saveNewPolicy").mockResolvedValue(false);
    const success = await component.onSave();
    expect(success).toBe(false);
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });
  it("deletePolicy does nothing in create mode", async () => {
    await component.deletePolicy();
    expect(dialogService.confirmDelete).not.toHaveBeenCalled();
    expect(policyService.deletePolicy).not.toHaveBeenCalled();
  });
});

describe("PolicyEditPageComponent – edit mode", () => {
  let component: PolicyEditPageComponent;
  let fixture: ComponentFixture<PolicyEditPageComponent>;
  let policyService: MockPolicyService;
  let router: Router;

  beforeEach(async () => {
    await createTestBed("TestPolicy");

    fixture = TestBed.createComponent(PolicyEditPageComponent);
    component = fixture.componentInstance;
    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it("should be in edit mode when name param is present", () => {
    expect(component.mode()).toBe("edit");
  });

  it("savePolicy calls savePolicyEdits in edit mode and navigates back", async () => {
    const spy = jest.spyOn(policyService, "savePolicyEdits").mockResolvedValue(true);
    const success = await component.onSave();
    expect(spy).toHaveBeenCalled();
    expect(success).toBe(true);
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES);
  });

  it("savePolicy does not navigate when savePolicyEdits returns false", async () => {
    jest.spyOn(policyService, "savePolicyEdits").mockResolvedValue(false);
    const success = await component.onSave();
    expect(success).toBe(false);
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  describe("deletePolicy", () => {
    let dialogService: MockDialogService;
    let notificationService: MockNotificationService;
    let pendingChangesService: MockPendingChangesService;

    beforeEach(() => {
      dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
      notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
      pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    });

    it("deletes the policy after confirmation and navigates back", async () => {
      await component.deletePolicy();
      expect(dialogService.confirmDelete).toHaveBeenCalledWith(expect.objectContaining({ items: ["TestPolicy"] }));
      expect(policyService.deletePolicy).toHaveBeenCalledWith("TestPolicy");
      expect(notificationService.success).toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES);
    });

    it("does not delete when the confirmation is cancelled", async () => {
      dialogService.confirmDelete.mockResolvedValue(false);
      await component.deletePolicy();
      expect(policyService.deletePolicy).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("shows the server message and stays on the page when the deletion fails", async () => {
      policyService.deletePolicy.mockRejectedValue(
        new HttpErrorResponse({ error: { result: { error: { message: "policy is in use" } } } })
      );
      await component.deletePolicy();
      expect(notificationService.error).toHaveBeenCalledWith(expect.stringContaining("policy is in use"));
      expect(notificationService.success).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("shows the server message and stays on the page when the response carries an error", async () => {
      policyService.deletePolicy.mockResolvedValue(
        new MockPiResponse<number>({ result: { status: false, error: { code: 905, message: "policy is in use" } } })
      );
      await component.deletePolicy();
      expect(notificationService.error).toHaveBeenCalledWith(expect.stringContaining("policy is in use"));
      expect(notificationService.success).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("shows a generic error when the failure carries no message", async () => {
      policyService.deletePolicy.mockRejectedValue(new Error("network down"));
      await component.deletePolicy();
      expect(notificationService.error).toHaveBeenCalledWith("Failed to delete policy. ");
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });
  });
});
