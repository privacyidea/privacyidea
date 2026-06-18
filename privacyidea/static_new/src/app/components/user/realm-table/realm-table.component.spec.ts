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
import { TestBed } from "@angular/core/testing";
import { of } from "rxjs";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MatDialog } from "@angular/material/dialog";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { Realm, RealmRow, RealmService, Realms } from "@services/realm/realm.service";
import { Resolver, ResolverService } from "@services/resolver/resolver.service";
import { SystemService } from "@services/system/system.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import {
  MockContentService,
  MockHttpResourceRef,
  MockNotificationService,
  MockPiResponse,
  MockRealmService,
  MockRouter,
  MockSystemService,
  MockTableUtilsService
} from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { RealmTableComponent } from "./realm-table.component";

class LocalMockMatDialog {
  result$ = of(true);

  open = jest.fn(() => ({
    afterClosed: () => this.result$
  }));
}

describe("RealmTableComponent", () => {
  let component: RealmTableComponent;
  let realmService: MockRealmService;
  let notificationService: MockNotificationService;
  let dialog: LocalMockMatDialog;
  let resolverService: MockResolverService;
  let router: Router;
  let pendingChangesService: MockPendingChangesService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RealmTableComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: SystemService, useClass: MockSystemService },
        { provide: ContentService, useClass: MockContentService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: MatDialog, useClass: LocalMockMatDialog },
        { provide: ResolverService, useClass: MockResolverService },
        { provide: Router, useClass: MockRouter },
        { provide: PendingChangesService, useClass: MockPendingChangesService }
      ]
    }).compileComponents();

    const fixture = TestBed.createComponent(RealmTableComponent);
    component = fixture.componentInstance;

    realmService = TestBed.inject(RealmService) as unknown as MockRealmService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    dialog = TestBed.inject(MatDialog) as unknown as LocalMockMatDialog;
    resolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
    router = TestBed.inject(Router);
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should have correct column keys", () => {
    expect(component.columnKeys).toEqual(["name", "isDefault", "resolvers", "actions"]);
  });

  it("nodeOptions should include All nodes and system nodes", () => {
    const options = component.nodeOptions();
    expect(options.length).toBe(3);
    expect(options[0]).toEqual({ label: "All nodes", value: "__all_nodes__" });
    expect(options[1]).toEqual({ label: "Node 1", value: "node-1" });
    expect(options[2]).toEqual({ label: "Node 2", value: "node-2" });
  });

  it("allNodeGroups should include NO_NODE_ID and all nodes", () => {
    const groups = component.allNodeGroups();
    expect(groups.length).toBe(3);
    expect(groups[0]).toEqual({ id: "", label: "All nodes" });
    expect(groups[1]).toEqual({ id: "node-1", label: "Node 1" });
    expect(groups[2]).toEqual({ id: "node-2", label: "Node 2" });
  });

  it("resolverOptions should map resolvername and type from ResolverService", () => {
    resolverService.setResolvers([
      {
        resolvername: "res1",
        type: "ldapresolver",
        censor_keys: [],
        data: {}
      },
      {
        resolvername: "res2",
        type: "sqlresolver",
        censor_keys: [],
        data: {}
      },
      {
        resolvername: "res3",
        type: "scimresolver",
        censor_keys: [],
        data: {}
      }
    ]);

    const options = component.resolverOptions();
    expect(options).toEqual(
      expect.arrayContaining([
        { name: "res1", type: "ldapresolver" },
        { name: "res2", type: "sqlresolver" },
        { name: "res3", type: "scimresolver" }
      ])
    );
    expect(options.length).toBe(3);
  });

  it("realmRows should build resolverGroups and resolversText", () => {
    const realms: Realms = {
      realmA: {
        default: true,
        resolver: [
          { name: "resGlobal", type: "ldap", node: "", priority: null },
          { name: "resNode", type: "sql", node: "node-1", priority: 5 }
        ]
      } as Realm
    };

    const ref = realmService.realmResource as unknown as MockHttpResourceRef<MockPiResponse<Realms> | undefined>;
    ref.set(MockPiResponse.fromValue<Realms>(realms));

    const rows = component.realmRows();
    expect(rows.length).toBe(1);

    const row = rows[0];
    expect(row.name).toBe("realmA");
    expect(row.isDefault).toBe(true);
    expect(row.resolverGroups.length).toBe(2);

    const globalGroup = row.resolverGroups.find((g) => g.nodeId === "");
    const nodeGroup = row.resolverGroups.find((g) => g.nodeId === "node-1");

    expect(globalGroup?.nodeLabel).toBe("All nodes");
    expect(globalGroup?.resolvers[0]).toEqual({
      name: "resGlobal",
      type: "ldap",
      priority: null
    });

    expect(nodeGroup?.nodeLabel).toBe("Node 1");
    expect(nodeGroup?.resolvers[0]).toEqual({
      name: "resNode",
      type: "sql",
      priority: 5
    });

    expect(row.resolversText).toContain("resGlobal ldap All nodes");
    expect(row.resolversText).toContain("resNode sql Node 1 5");
  });

  it("realmRows should filter by selected node", () => {
    const realms: Realms = {
      realmA: {
        default: false,
        resolver: [
          { name: "resGlobal", type: "ldap", node: "", priority: null },
          { name: "resNode", type: "sql", node: "node-1", priority: 5 }
        ]
      } as Realm,
      realmB: {
        default: false,
        resolver: [{ name: "resOther", type: "http", node: "node-2", priority: 3 }]
      } as Realm
    };

    const ref = realmService.realmResource as unknown as MockHttpResourceRef<MockPiResponse<Realms> | undefined>;
    ref.set(MockPiResponse.fromValue<Realms>(realms));

    component.selectedNode.set("node-1");
    const rowsNode1 = component.realmRows();
    expect(rowsNode1.length).toBe(1);
    expect(rowsNode1[0].name).toBe("realmA");

    component.selectedNode.set("node-2");
    const rowsNode2 = component.realmRows();
    expect(rowsNode2.length).toBe(1);
    expect(rowsNode2[0].name).toBe("realmB");

    component.selectedNode.set("non-existing");
    const rowsNone = component.realmRows();
    expect(rowsNone.length).toBe(0);
  });

  it("onNewRealmNodeResolversChange should set resolvers with null priority", () => {
    component.newRealmNodeResolvers.set({});
    component.onNewRealmNodeResolversChange("node-1", ["res1", "res2"]);

    const map = component.newRealmNodeResolvers();
    expect(map["node-1"]).toEqual([
      { name: "res1", priority: null },
      { name: "res2", priority: null }
    ]);
  });

  it("onNewRealmNodeResolversChange should keep existing priorities", () => {
    component.newRealmNodeResolvers.set({
      "node-1": [{ name: "res1", priority: 10 }]
    });

    component.onNewRealmNodeResolversChange("node-1", ["res1", "res2"]);

    const map = component.newRealmNodeResolvers();
    expect(map["node-1"]).toEqual([
      { name: "res1", priority: 10 },
      { name: "res2", priority: null }
    ]);
  });

  it("setNewRealmResolverPriority should set and clamp priority, allow null", () => {
    component.newRealmNodeResolvers.set({
      "node-1": [{ name: "res1", priority: null }]
    });

    component.setNewRealmResolverPriority({ nodeId: "node-1", resolverName: "res1", priority: String(10) });
    expect(component.newRealmNodeResolvers()["node-1"][0].priority).toBe(10);

    component.setNewRealmResolverPriority({ nodeId: "node-1", resolverName: "res1", priority: String(0) });
    expect(component.newRealmNodeResolvers()["node-1"][0].priority).toBe(1);

    component.setNewRealmResolverPriority({ nodeId: "node-1", resolverName: "res1", priority: String(2000) });
    expect(component.newRealmNodeResolvers()["node-1"][0].priority).toBe(999);

    component.setNewRealmResolverPriority({ nodeId: "node-1", resolverName: "res1", priority: String("") });
    expect(component.newRealmNodeResolvers()["node-1"][0].priority).toBeNull();
  });

  it("setEditResolverPriority should set and clamp priority, allow null", () => {
    component.editNodeResolvers.set({
      "node-1": [{ name: "res1", priority: 5 }]
    });

    component.setEditResolverPriority("node-1", "res1", String(20));
    expect(component.editNodeResolvers()["node-1"][0].priority).toBe(20);

    component.setEditResolverPriority("node-1", "res1", String(0));
    expect(component.editNodeResolvers()["node-1"][0].priority).toBe(1);

    component.setEditResolverPriority("node-1", "res1", String(2000));
    expect(component.editNodeResolvers()["node-1"][0].priority).toBe(999);

    component.setEditResolverPriority("node-1", "res1", "");
    expect(component.editNodeResolvers()["node-1"][0].priority).toBeNull();
  });

  it("canSubmitNewRealm should depend on name and isCreatingRealm", () => {
    component.newRealmName.set("");
    component.isCreatingRealm.set(false);
    expect(component.canSubmitNewRealm()).toBe(false);

    component.newRealmName.set("  ");
    expect(component.canSubmitNewRealm()).toBe(false);

    component.newRealmName.set("realm");
    component.isCreatingRealm.set(true);
    expect(component.canSubmitNewRealm()).toBe(false);

    component.isCreatingRealm.set(false);
    expect(component.canSubmitNewRealm()).toBe(true);
  });

  it("resetCreateForm should clear name and resolvers", () => {
    component.newRealmName.set("realm");
    component.newRealmNodeResolvers.set({ "node-1": [{ name: "res1", priority: 1 }] });

    component.resetCreateForm();

    expect(component.newRealmName()).toBe("");
    expect(component.newRealmNodeResolvers()).toEqual({});
  });

  it("onCreateRealm should resolve false when cannot submit", async () => {
    component.newRealmName.set("");
    component.isCreatingRealm.set(false);

    const result = await component.onCreateRealm();

    expect(result).toBe(false);
    expect(realmService.createRealm).not.toHaveBeenCalled();
  });

  it("onCreateRealm should create realm with global resolvers and optional priorities", async () => {
    component.newRealmName.set("realmA");
    component.newRealmNodeResolvers.set({
      "": [
        { name: "res1", priority: 10 },
        { name: "res2", priority: null }
      ],
      "node-1": [
        { name: "res3", priority: 5 },
        { name: "res4", priority: null }
      ]
    });

    const result = await component.onCreateRealm();

    expect(result).toBe(true);
    expect(realmService.createRealm).toHaveBeenCalledTimes(2);

    const callGlobal = (realmService.createRealm as jest.Mock).mock.calls[0];
    expect(callGlobal[0]).toBe("realmA");
    expect(callGlobal[1]).toBe("");
    expect(callGlobal[2]).toEqual([{ name: "res1", priority: 10 }, { name: "res2" }]);

    const callNode = (realmService.createRealm as jest.Mock).mock.calls[1];
    expect(callNode[0]).toBe("realmA");
    expect(callNode[1]).toBe("node-1");
    expect(callNode[2]).toEqual([{ name: "res3", priority: 5 }, { name: "res4" }]);

    expect(notificationService.success).toHaveBeenCalledWith("Realm created.");
    expect(component.newRealmName()).toBe("");
    expect(component.newRealmNodeResolvers()).toEqual({});
    expect(component.isCreatingRealm()).toBe(false);
    expect(realmService.realmResource.reload).toHaveBeenCalled();
  });

  it("onCreateRealm should create realm with empty resolver list when none configured", async () => {
    component.newRealmName.set("realmEmpty");
    component.newRealmNodeResolvers.set({});

    const result = await component.onCreateRealm();

    expect(result).toBe(true);
    expect(realmService.createRealm).toHaveBeenCalledTimes(1);
    const call = (realmService.createRealm as jest.Mock).mock.calls[0];
    expect(call[0]).toBe("realmEmpty");
    expect(call[1]).toBe("");
    expect(call[2]).toEqual([]);
  });

  it("startEditRealm should initialize editing state and maps", () => {
    const row: RealmRow = {
      name: "realmA",
      isDefault: false,
      resolversText: "",
      resolverGroups: [
        {
          nodeId: "",
          nodeLabel: "All nodes",
          resolvers: [{ name: "res1", type: "ldap", priority: null }]
        },
        {
          nodeId: "node-1",
          nodeLabel: "Node 1",
          resolvers: [{ name: "res2", type: "sql", priority: 5 }]
        }
      ]
    };

    component.startEditRealm(row);

    expect(component.editingRealmName()).toBe("realmA");

    const original = component.editOriginalNodeResolvers();
    const editable = component.editNodeResolvers();

    expect(original).toEqual({
      "": [{ name: "res1", priority: null }],
      "node-1": [{ name: "res2", priority: 5 }]
    });
    expect(editable).toEqual(original);
  });

  it("cancelEditRealm should reset editing state", () => {
    component.editingRealmName.set("realmA");
    component.editOriginalNodeResolvers.set({ "node-1": [{ name: "res1", priority: 1 }] });
    component.editNodeResolvers.set({ "node-1": [{ name: "res1", priority: 2 }] });
    component.isSavingEditedRealm.set(true);

    component.cancelEditRealm();

    expect(component.editingRealmName()).toBeNull();
    expect(component.editOriginalNodeResolvers()).toEqual({});
    expect(component.editNodeResolvers()).toEqual({});
    expect(component.isSavingEditedRealm()).toBe(false);
  });

  it("canSaveEditedRealm should be true only when same realm and not saving", () => {
    const row = { name: "realmA" } as unknown as RealmRow;

    component.editingRealmName.set("realmA");
    component.isSavingEditedRealm.set(false);
    expect(component.canSaveEditedRealm(row)).toBe(true);

    component.isSavingEditedRealm.set(true);
    expect(component.canSaveEditedRealm(row)).toBe(false);

    component.editingRealmName.set("other");
    component.isSavingEditedRealm.set(false);
    expect(component.canSaveEditedRealm(row)).toBe(false);
  });

  it("saveEditedRealm should show error when no resolvers configured", () => {
    const row = { name: "realmA" } as unknown as RealmRow;
    component.editingRealmName.set("realmA");
    component.editNodeResolvers.set({});

    component.saveEditedRealm(row);

    expect(notificationService.warning).toHaveBeenCalledWith("No resolvers configured.");
    expect(realmService.createRealm).not.toHaveBeenCalled();
    expect(component.isSavingEditedRealm()).toBe(false);
  });

  it("saveEditedRealm should send updated resolvers and reset editing state", () => {
    const row = { name: "realmA" } as unknown as RealmRow;

    component.editingRealmName.set("realmA");
    component.editNodeResolvers.set({
      "": [
        { name: "res1", priority: 10 },
        { name: "res2", priority: null }
      ],
      "node-1": [{ name: "res3", priority: 7 }]
    });

    component.saveEditedRealm(row);

    expect(realmService.createRealm).toHaveBeenCalledTimes(2);

    const callGlobal = (realmService.createRealm as jest.Mock).mock.calls[0];
    expect(callGlobal[0]).toBe("realmA");
    expect(callGlobal[1]).toBe("");
    expect(callGlobal[2]).toEqual([{ name: "res1", priority: 10 }, { name: "res2" }]);

    const callNode = (realmService.createRealm as jest.Mock).mock.calls[1];
    expect(callNode[0]).toBe("realmA");
    expect(callNode[1]).toBe("node-1");
    expect(callNode[2]).toEqual([{ name: "res3", priority: 7 }]);

    expect(notificationService.success).toHaveBeenCalledWith('Realm "realmA" updated.');
    expect(component.editingRealmName()).toBeNull();
    expect(component.isSavingEditedRealm()).toBe(false);
    expect(realmService.realmResource.reload).toHaveBeenCalled();
  });

  it("onDeleteRealm should do nothing when row has no name", () => {
    component.onDeleteRealm({} as unknown as RealmRow);
    expect(dialog.open).not.toHaveBeenCalled();
  });

  it("onDeleteRealm should delete realm when confirmed", () => {
    dialog.result$ = of(true);
    const row = { name: "realmA" } as unknown as RealmRow;

    component.onDeleteRealm(row);

    expect(dialog.open).toHaveBeenCalled();
    expect(realmService.deleteRealm).toHaveBeenCalledWith("realmA");
    expect(notificationService.success).toHaveBeenCalledWith('Realm "realmA" deleted.');
    expect(realmService.realmResource.reload).toHaveBeenCalled();
  });

  it("onDeleteRealm should not delete when dialog is cancelled", () => {
    dialog.result$ = of(false);
    const row = { name: "realmA" } as unknown as RealmRow;

    component.onDeleteRealm(row);

    expect(dialog.open).toHaveBeenCalled();
    expect(realmService.deleteRealm).not.toHaveBeenCalled();
  });

  it("onSetDefaultRealm should do nothing when row has no name", () => {
    component.onSetDefaultRealm({} as unknown as RealmRow);
    expect(realmService.setDefaultRealm).not.toHaveBeenCalled();
  });

  it("onSetDefaultRealm should call service and reload resources", () => {
    const row = { name: "realmA" } as unknown as RealmRow;

    component.onSetDefaultRealm(row);

    expect(realmService.setDefaultRealm).toHaveBeenCalledWith("realmA");
    expect(notificationService.success).toHaveBeenCalledWith('Realm "realmA" set as default.');
    expect(realmService.realmResource.reload).toHaveBeenCalled();
    expect(realmService.defaultRealmResource.reload).toHaveBeenCalled();
  });

  it("onClickResolver should redirect to resolver details page", () => {
    const resolver = { resolvername: "res1", type: "ldapresolver" } as unknown as Resolver;
    resolverService.setResolvers([resolver]);

    component.onClickResolver("res1");

    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.USERS_RESOLVERS_DETAILS + "res1");
  });

  it("onClickResolver should do nothing if resolver not found", () => {
    resolverService.setResolvers([]);
    component.onClickResolver("non-existing");
    expect(dialog.open).not.toHaveBeenCalled();
  });

  describe("pending changes", () => {
    it("registers hasChanges, validChanges, and save in ngOnInit", () => {
      expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerValidChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerSave).toHaveBeenCalled();
    });

    it("hasChanges reflects newRealmName, newRealmNodeResolvers, and edit diff", () => {
      const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;

      expect(fn()).toBe(false);

      component.newRealmName.set("newRealm");
      expect(fn()).toBe(true);
      component.newRealmName.set("");

      component.newRealmNodeResolvers.set({ node1: [{ name: "res", priority: null }] });
      expect(fn()).toBe(true);
      component.newRealmNodeResolvers.set({});

      // Entering edit mode alone (no diff) should NOT trigger hasChanges
      component.editingRealmName.set("someRealm");
      expect(fn()).toBe(false);

      // Edit diff triggers hasChanges
      component.editNodeResolvers.set({ node1: [{ name: "res", priority: 1 }] });
      expect(fn()).toBe(true);
    });

    it("validChanges reflects canSubmitNewRealm", () => {
      const fn = (pendingChangesService.registerValidChanges as jest.Mock).mock.calls[0][0] as () => boolean;
      expect(fn()).toBe(false);

      component.newRealmName.set("validName");
      expect(fn()).toBe(true);

      component.newRealmName.set("invalid name with spaces");
      expect(fn()).toBe(false);
    });

    it("ngOnDestroy clears all pending-changes registrations", () => {
      component.ngOnDestroy();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    });
  });
});
