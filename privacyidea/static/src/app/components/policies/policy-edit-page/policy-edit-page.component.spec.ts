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
import { Component, input, output, Provider, signal } from "@angular/core";
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
import { AuthService } from "@services/auth/auth.service";
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
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { of } from "rxjs";

@Component({ selector: "app-policy-panel-edit", standalone: true, template: "" })
class MockPanel {
  policy = input.required<PolicyDetail>();
  nameTaken = input<boolean>(false);
  activeTab = input<PolicyTab>("actions");
  actionFilter = input<string>("");
  searchInHeader = input<boolean>(false);
  policyEdit = output<Partial<PolicyDetail>>();
  activeTabChange = output<PolicyTab>();
  actionFilterChange = output<string>();
  searchAnchor = signal<HTMLElement | undefined>(undefined);
  searchField = signal<Partial<PolicyActionSearchComponent> | undefined>(undefined);
}

function createTestBed(paramName: string | null, extraProviders: Provider[] = []) {
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
      { provide: NotificationService, useClass: MockNotificationService },
      ...extraProviders
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

  it("canSave returns false while check_all_resolvers is set without a resolver", () => {
    component.addPolicyEdit({ name: "ValidName", resolver: ["resolver1"], check_all_resolvers: true });
    expect(component.canSave()).toBe(true);
    component.addPolicyEdit({ resolver: [] });
    expect(component.canSave()).toBe(false);
    component.addPolicyEdit({ check_all_resolvers: false });
    expect(component.canSave()).toBe(true);
  });

  const mockPanel = (): MockPanel => fixture.debugElement.query(By.directive(MockPanel)).componentInstance;

  describe("name collision", () => {
    const existingPolicy = (name: string): PolicyDetail => ({ ...policyService.getEmptyPolicy(), name });
    const panel = () => fixture.debugElement.query(By.directive(MockPanel)).componentInstance as MockPanel;

    beforeEach(() => {
      policyService.allPolicies.set([existingPolicy("helpdesk"), existingPolicy("admin")]);
    });

    it("does not report a collision for a free name", () => {
      component.addPolicyEdit({ name: "new-policy" });
      expect(component.nameTaken()).toBe(false);
      expect(component.canSave()).toBe(true);
    });

    it("reports a collision with an existing policy and blocks saving", () => {
      component.addPolicyEdit({ name: "helpdesk" });
      expect(component.nameTaken()).toBe(true);
      expect(component.canSave()).toBe(false);
    });

    it("ignores the case of the name, which MySQL and MariaDB do as well", () => {
      component.addPolicyEdit({ name: "Helpdesk" });
      expect(component.nameTaken()).toBe(true);
      expect(component.canSave()).toBe(false);
    });

    it("allows saving again once the name is changed to a free one", () => {
      component.addPolicyEdit({ name: "helpdesk" });
      component.addPolicyEdit({ name: "helpdesk2" });
      expect(component.canSave()).toBe(true);
    });

    it("reports the collision for a name that was applied by a template", () => {
      component.addPolicyEdit({ name: "admin", scope: "admin" });
      expect(component.nameTaken()).toBe(true);
      expect(component.canSave()).toBe(false);
    });

    it("tells the collision to the panel", () => {
      fixture.detectChanges();
      expect(panel().nameTaken()).toBe(false);

      component.addPolicyEdit({ name: "helpdesk" });
      fixture.detectChanges();

      expect(panel().nameTaken()).toBe(true);
    });

    it("registers the collision with the pending changes, so that leaving the page cannot save it", () => {
      const pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
      component.addPolicyEdit({ name: "helpdesk" });
      expect(pendingChangesService.registerValidChanges).toHaveBeenCalledWith(expect.any(Function));
      const hasValidChanges = pendingChangesService.registerValidChanges.mock.calls[0][0] as () => boolean;
      expect(hasValidChanges()).toBe(false);
    });

    it("does not report a collision while the save is pending, when the service already lists the new policy", async () => {
      component.addPolicyEdit({ name: "new-policy" });
      let nameTakenDuringSave: boolean | undefined;
      jest.spyOn(policyService, "saveNewPolicy").mockImplementation(async () => {
        policyService.allPolicies.set([...policyService.allPolicies(), existingPolicy("new-policy")]);
        nameTakenDuringSave = component.nameTaken();
        return true;
      });

      await component.onSave();

      expect(nameTakenDuringSave).toBe(false);
      expect(component.nameTaken()).toBe(false);
    });

    it("still reports a collision for another name that is typed while the save is pending", async () => {
      component.addPolicyEdit({ name: "new-policy" });
      let finishSave: (success: boolean) => void = () => undefined;
      jest
        .spyOn(policyService, "saveNewPolicy")
        .mockReturnValue(new Promise<boolean>((resolve) => (finishSave = resolve)));

      const saving = component.onSave();
      component.addPolicyEdit({ name: "helpdesk" });

      expect(component.nameTaken()).toBe(true);
      expect(component.canSave()).toBe(false);

      finishSave(false);
      await saving;
    });

    it("checks the name again after a failed save", async () => {
      component.addPolicyEdit({ name: "new-policy" });
      jest.spyOn(policyService, "saveNewPolicy").mockImplementation(async () => {
        policyService.allPolicies.set([...policyService.allPolicies(), existingPolicy("new-policy")]);
        return false;
      });

      await component.onSave();

      expect(component.nameTaken()).toBe(true);
      expect(component.canSave()).toBe(false);
    });

    it("checks the name again when the save throws", async () => {
      component.addPolicyEdit({ name: "new-policy" });
      jest.spyOn(policyService, "saveNewPolicy").mockImplementation(async () => {
        policyService.allPolicies.set([...policyService.allPolicies(), existingPolicy("new-policy")]);
        throw new Error("boom");
      });

      await expect(component.onSave()).rejects.toThrow("boom");

      expect(component.nameTaken()).toBe(true);
      expect(component.canSave()).toBe(false);
    });

    it("does not save a taken name when the save is called directly", async () => {
      component.addPolicyEdit({ name: "helpdesk" });

      expect(await component.onSave()).toBe(false);

      expect(policyService.saveNewPolicy).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("tells the user why a taken name is not saved", async () => {
      const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
      component.addPolicyEdit({ name: "helpdesk" });

      await component.onSave();

      expect(notificationService.error).toHaveBeenCalledWith("A policy with this name already exists.");
    });

    it("does not save a name that the policy list reveals as taken after the pending-changes dialog opened", async () => {
      const pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
      const hasValidChanges = pendingChangesService.registerValidChanges.mock.calls[0][0] as () => boolean;
      const saveFromDialog = pendingChangesService.registerSave.mock.calls[0][0] as () => Promise<boolean>;
      component.addPolicyEdit({ name: "late-policy" });
      expect(hasValidChanges()).toBe(true);

      policyService.allPolicies.set([...policyService.allPolicies(), existingPolicy("late-policy")]);

      expect(await saveFromDialog()).toBe(false);
      expect(policyService.saveNewPolicy).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("ignores a second save while one runs, without reporting a collision", async () => {
      component.addPolicyEdit({ name: "new-policy" });
      let finishSave: (success: boolean) => void = () => undefined;
      jest
        .spyOn(policyService, "saveNewPolicy")
        .mockReturnValue(new Promise<boolean>((resolve) => (finishSave = resolve)));
      const saving = component.onSave();
      component.addPolicyEdit({ name: "helpdesk" });
      const notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

      expect(await component.onSave()).toBe(false);
      expect(notificationService.error).not.toHaveBeenCalled();

      finishSave(false);
      await saving;
    });

    it("disables saving while the save is pending and enables it again after a failure", async () => {
      component.addPolicyEdit({ name: "new-policy" });
      let finishSave: (success: boolean) => void = () => undefined;
      jest
        .spyOn(policyService, "saveNewPolicy")
        .mockReturnValue(new Promise<boolean>((resolve) => (finishSave = resolve)));

      const saving = component.onSave();

      expect(component.canSave()).toBe(false);
      expect(await component.onSave()).toBe(false);
      expect(policyService.saveNewPolicy).toHaveBeenCalledTimes(1);

      finishSave(false);
      await saving;

      expect(component.canSave()).toBe(true);
    });
  });

  function anchorAt(top: number): HTMLElement {
    const header: HTMLElement = fixture.debugElement.query(By.directive(StickyHeaderDirective)).nativeElement;
    jest.spyOn(header, "getBoundingClientRect").mockReturnValue({ bottom: 100 } as DOMRect);
    const anchor = document.createElement("div");
    jest.spyOn(anchor, "getBoundingClientRect").mockReturnValue({ top } as DOMRect);
    return anchor;
  }

  function scrollSearchAnchorTo(anchorTop: number) {
    mockPanel().searchAnchor.set(anchorAt(anchorTop));

    fixture.debugElement.query(By.directive(ScrollToTopDirective)).nativeElement.dispatchEvent(new Event("scroll"));
    fixture.detectChanges();
  }

  const headerSearchField = () => fixture.debugElement.query(By.directive(PolicyActionSearchComponent));
  const headerSearchShown = () => !headerSearchField().nativeElement.classList.contains("hidden");

  it("keeps the action search in the header but hidden until the header reaches it", () => {
    scrollSearchAnchorTo(101);

    expect(headerSearchField()).not.toBeNull();
    expect(headerSearchShown()).toBe(false);
  });

  it("shows the action search in the header once the header touches its top edge", () => {
    scrollSearchAnchorTo(100);

    expect(headerSearchShown()).toBe(true);
  });

  it("gives the action search back to the tab when scrolled up again", () => {
    scrollSearchAnchorTo(40);
    scrollSearchAnchorTo(140);

    expect(headerSearchShown()).toBe(false);
  });

  it("keeps the action search hidden in the header on the conditions tab", () => {
    component.activeTab.set("conditions");
    scrollSearchAnchorTo(40);

    expect(headerSearchShown()).toBe(false);
  });

  function latestResizeObserver(): { observe: jest.Mock; notify: () => void } {
    const { mock } = ResizeObserver as unknown as jest.Mock;
    return { observe: mock.results.at(-1)!.value.observe, notify: () => mock.calls.at(-1)![0]([]) };
  }

  it("re-checks when content above shifts the field without a scroll", () => {
    scrollSearchAnchorTo(101);
    jest.spyOn(mockPanel().searchAnchor()!, "getBoundingClientRect").mockReturnValue({ top: 100 } as DOMRect);

    latestResizeObserver().notify();
    fixture.detectChanges();

    expect(headerSearchShown()).toBe(true);
  });

  it("re-checks a returning actions tab against its new anchor", () => {
    scrollSearchAnchorTo(40);
    component.activeTab.set("conditions");
    mockPanel().searchAnchor.set(undefined);
    fixture.detectChanges();

    const anchor = anchorAt(140);
    component.activeTab.set("actions");
    mockPanel().searchAnchor.set(anchor);
    fixture.detectChanges();
    const observer = latestResizeObserver();
    observer.notify();
    fixture.detectChanges();

    expect(observer.observe).toHaveBeenCalledWith(anchor);
    expect(headerSearchShown()).toBe(false);
  });

  describe("focus handoff", () => {
    const headerSearchInput = (): HTMLInputElement => headerSearchField().query(By.css("input")).nativeElement;

    beforeEach(() => {
      component.actionFilter.set("token");
    });

    it("moves focus and caret into the header copy when the field moves up", async () => {
      mockPanel().searchField.set({ focusState: () => ({ start: 1, end: 3, direction: "backward" }) });

      scrollSearchAnchorTo(100);
      await fixture.whenStable();

      const input = headerSearchInput();
      expect(document.activeElement).toBe(input);
      expect([input.selectionStart, input.selectionEnd, input.selectionDirection]).toEqual([1, 3, "backward"]);
    });

    it("moves focus from the clear button to the header copy's clear button", async () => {
      mockPanel().searchField.set({ focusState: () => "clear-button" });

      scrollSearchAnchorTo(100);
      await fixture.whenStable();

      expect(document.activeElement).toBe(headerSearchField().query(By.css("app-clear-button button")).nativeElement);
    });

    it("moves focus and caret back to the tab copy when the field returns", async () => {
      const takeFocus = jest.fn();
      mockPanel().searchField.set({ focusState: () => null, takeFocus });
      scrollSearchAnchorTo(100);
      headerSearchInput().focus();
      headerSearchInput().setSelectionRange(2, 4, "backward");

      scrollSearchAnchorTo(140);
      await fixture.whenStable();

      expect(takeFocus).toHaveBeenCalledWith({ start: 2, end: 4, direction: "backward" });
    });

    it("leaves focus alone when the search field does not have it", async () => {
      mockPanel().searchField.set({ focusState: () => null });

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

  describe("renaming", () => {
    const existingPolicy = (name: string): PolicyDetail => ({ ...policyService.getEmptyPolicy(), name });

    beforeEach(() => {
      policyService.allPolicies.set([existingPolicy("TestPolicy"), existingPolicy("helpdesk")]);
      fixture.detectChanges();
    });

    it("loads the policy that is edited", () => {
      expect(component.policy().name).toBe("TestPolicy");
    });

    it("does not count the policy being edited as a collision with itself", () => {
      component.addPolicyEdit({ description: "changed" });
      expect(component.nameTaken()).toBe(false);
      expect(component.canSave()).toBe(true);
    });

    it("does not report a collision when the name is typed back to the original one", () => {
      component.addPolicyEdit({ name: "TestPolicy2" });
      component.addPolicyEdit({ name: "TestPolicy" });
      expect(component.nameTaken()).toBe(false);
      expect(component.canSave()).toBe(true);
    });

    it("allows renaming to a free name", () => {
      component.addPolicyEdit({ name: "renamed" });
      expect(component.nameTaken()).toBe(false);
      expect(component.canSave()).toBe(true);
    });

    it("reports a collision when renaming to the name of another policy and blocks saving", () => {
      component.addPolicyEdit({ name: "helpdesk" });
      expect(component.nameTaken()).toBe(true);
      expect(component.canSave()).toBe(false);
    });

    it("registers the colliding rename as invalid with the pending changes, so that leaving the page cannot save it", () => {
      component.addPolicyEdit({ name: "helpdesk", description: "changed" });
      const pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
      const hasValidChanges = pendingChangesService.registerValidChanges.mock.calls[0][0] as () => boolean;
      expect(hasValidChanges()).toBe(false);
    });

    it("does not report a collision while the save is pending, when the service already lists the renamed policy", async () => {
      component.addPolicyEdit({ name: "renamed" });
      let nameTakenDuringSave: boolean | undefined;
      jest.spyOn(policyService, "savePolicyEdits").mockImplementation(async () => {
        policyService.allPolicies.set([existingPolicy("renamed"), existingPolicy("helpdesk")]);
        nameTakenDuringSave = component.nameTaken();
        return true;
      });

      await component.onSave();

      expect(nameTakenDuringSave).toBe(false);
      expect(component.nameTaken()).toBe(false);
    });

    it("allows changing the case of the own name", () => {
      component.addPolicyEdit({ name: "testpolicy" });
      expect(component.nameTaken()).toBe(false);
      expect(component.canSave()).toBe(true);
    });

    it("reports a collision when renaming to a case variant of the name of another policy", () => {
      component.addPolicyEdit({ name: "HelpDesk" });
      expect(component.nameTaken()).toBe(true);
      expect(component.canSave()).toBe(false);
    });

    it("checks the name again after a failed save", async () => {
      component.addPolicyEdit({ name: "renamed" });
      jest.spyOn(policyService, "savePolicyEdits").mockImplementation(async () => {
        policyService.allPolicies.set([...policyService.allPolicies(), existingPolicy("renamed")]);
        return false;
      });

      await component.onSave();

      expect(component.nameTaken()).toBe(true);
      expect(component.canSave()).toBe(false);
    });

    it("does not send a rename to the name of another policy when the save is called directly", async () => {
      component.addPolicyEdit({ name: "helpdesk", description: "changed" });

      expect(await component.onSave()).toBe(false);

      expect(policyService.savePolicyEdits).not.toHaveBeenCalled();
    });
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

describe("PolicyEditPageComponent – copy", () => {
  let component: PolicyEditPageComponent;
  let fixture: ComponentFixture<PolicyEditPageComponent>;
  let policyService: MockPolicyService;
  let dialogService: MockDialogService;
  let pendingChangesService: MockPendingChangesService;
  let authService: MockAuthService;
  let router: Router;

  const storedPolicy = (): PolicyDetail => ({
    ...policyService.getEmptyPolicy(),
    name: "TestPolicy",
    description: "stored"
  });
  const copyButton = (): HTMLButtonElement | undefined =>
    Array.from<HTMLButtonElement>(fixture.nativeElement.querySelectorAll(".sticky-controls button")).find((button) =>
      button.textContent?.includes("Copy")
    );

  const setUp = async (paramName: string | null) => {
    await createTestBed(paramName, [{ provide: AuthService, useClass: MockAuthService }]);
    fixture = TestBed.createComponent(PolicyEditPageComponent);
    component = fixture.componentInstance;
    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    router = TestBed.inject(Router);
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["policywrite"] });
    policyService.allPolicies.set([storedPolicy()]);
    fixture.detectChanges();
  };

  describe("in edit mode", () => {
    beforeEach(() => setUp("TestPolicy"));

    it("offers the copy next to the save", () => {
      expect(copyButton()).toBeDefined();
    });

    it("is not offered without the right to write policies", () => {
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });
      fixture.detectChanges();
      expect(copyButton()).toBeUndefined();
    });

    it("asks for the name of the copy, starting from the stored name", async () => {
      dialogService.openDialogAsync.mockResolvedValue(null);
      await component.onCopy();
      expect(dialogService.openDialogAsync).toHaveBeenCalledWith(expect.objectContaining({ data: "TestPolicy" }));
      expect(policyService.saveNewPolicy).not.toHaveBeenCalled();
    });

    it("creates the copy from the form with the edits not yet saved and leaves the original alone", async () => {
      dialogService.openDialogAsync.mockResolvedValue("TestPolicyCopy");
      component.addPolicyEdit({ description: "edited", priority: 7 });

      await component.onCopy();

      expect(policyService.saveNewPolicy).toHaveBeenCalledWith(
        expect.objectContaining({ name: "TestPolicyCopy", description: "edited", priority: 7 })
      );
      expect(policyService.savePolicyEdits).not.toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES);
    });

    it("names the copy as chosen in the dialog, not as the name field of the form says", async () => {
      dialogService.openDialogAsync.mockResolvedValue("FromDialog");
      component.addPolicyEdit({ name: "TypedInForm" });

      await component.onCopy();

      expect(policyService.saveNewPolicy).toHaveBeenCalledWith(expect.objectContaining({ name: "FromDialog" }));
    });

    it("stays on the page, with the save available again, when the copy fails", async () => {
      dialogService.openDialogAsync.mockResolvedValue("TestPolicyCopy");
      policyService.saveNewPolicy.mockResolvedValue(false);
      component.addPolicyEdit({ description: "edited" });

      await component.onCopy();

      expect(router.navigateByUrl).not.toHaveBeenCalled();
      expect(component.canSave()).toBe(true);
    });

    it("blocks a second copy and the save while the copy is created", async () => {
      dialogService.openDialogAsync.mockResolvedValue("TestPolicyCopy");
      let finish!: (created: boolean) => void;
      let creationStarted!: () => void;
      const started = new Promise<void>((resolve) => (creationStarted = resolve));
      policyService.saveNewPolicy.mockImplementation(() => {
        creationStarted();
        return new Promise<boolean>((resolve) => (finish = resolve));
      });
      component.addPolicyEdit({ description: "edited" });

      const copying = component.onCopy();
      await started;
      fixture.detectChanges();

      expect(component.canSave()).toBe(false);
      expect(copyButton()!.disabled).toBe(true);
      await component.onCopy();
      expect(dialogService.openDialogAsync).toHaveBeenCalledTimes(1);

      finish(true);
      await copying;
    });
  });

  describe("in create mode", () => {
    beforeEach(() => setUp(null));

    it("is not offered, because the save already creates a new policy", () => {
      expect(copyButton()).toBeUndefined();
    });
  });
});
