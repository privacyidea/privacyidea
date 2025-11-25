/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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

import { RealmTableComponent } from "./realm-table.component";
import { RealmService, Realms } from "../../../services/realm/realm.service";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { ContentService } from "../../../services/content/content.service";
import { SystemService } from "../../../services/system/system.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { MatDialog } from "@angular/material/dialog";
import {
  MockContentService,
  MockHttpResourceRef,
  MockNotificationService,
  MockPiResponse,
  MockRealmService,
  MockSystemService,
  MockTableUtilsService,
} from "../../../../testing/mock-services";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ResolverService } from "../../../services/resolver/resolver.service";
import { MockResolverService } from "../../../../testing/mock-services/mock-resolver-service";

class LocalMockMatDialog {
  result$ = of(true);

  open = jest.fn(() => ({
    afterClosed: () => this.result$
  }));
}

describe("RealmTableComponent", () => {
  let component: RealmTableComponent;
  let realmService: MockRealmService;
  let systemService: MockSystemService;
  let notificationService: MockNotificationService;
  let dialog: LocalMockMatDialog;
  let resolverService: MockResolverService;

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
        { provide: ResolverService, useClass: MockResolverService }
      ]
    }).compileComponents();

    const fixture = TestBed.createComponent(RealmTableComponent);
    component = fixture.componentInstance;

    realmService = TestBed.inject(RealmService) as unknown as MockRealmService;
    systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    dialog = TestBed.inject(MatDialog) as unknown as LocalMockMatDialog;
    resolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;

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
    const realms = {
      realmA: {
        default: true,
        resolver: [
          { name: "resGlobal", type: "ldap", node: "", priority: null },
          { name: "resNode", type: "sql", node: "node-1", priority: 5 }
        ]
      }
    } as any;

    const ref = realmService.realmResource as unknown as MockHttpResourceRef<MockPiResponse<Realms> | undefined>;
    ref.set(MockPiResponse.fromValue<Realms>(realms as any));

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
    const realms = {
      realmA: {
        default: false,
        resolver: [
          { name: "resGlobal", type: "ldap", node: "", priority: null },
          { name: "resNode", type: "sql", node: "node-1", priority: 5 }
        ]
      },
      realmB: {
        default: false,
        resolver: [
          { name: "resOther", type: "http", node: "node-2", priority: 3 }
        ]
      }
    } as any;

    const ref = realmService.realmResource as unknown as MockHttpResourceRef<MockPiResponse<Realms> | undefined>;
    ref.set(MockPiResponse.fromValue<Realms>(realms as any));

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

    component.setNewRealmResolverPriority("node-1", "res1", 10);
    expect(component.newRealmNodeResolvers()["node-1"][0].priority).toBe(10);

    component.setNewRealmResolverPriority("node-1", "res1", 0);
    expect(component.newRealmNodeResolvers()["node-1"][0].priority).toBe(1);

    component.setNewRealmResolverPriority("node-1", "res1", 2000);
    expect(component.newRealmNodeResolvers()["node-1"][0].priority).toBe(999);

    component.setNewRealmResolverPriority("node-1", "res1", "");
    expect(component.newRealmNodeResolvers()["node-1"][0].priority).toBeNull();
  });

  it("setEditResolverPriority should set and clamp priority, allow null", () => {
    component.editNodeResolvers.set({
      "node-1": [{ name: "res1", priority: 5 }]
    });

    component.setEditResolverPriority("node-1", "res1", 20);
    expect(component.editNodeResolvers()["node-1"][0].priority).toBe(20);

    component.setEditResolverPriority("node-1", "res1", 0);
    expect(component.editNodeResolvers()["node-1"][0].priority).toBe(1);

    component.setEditResolverPriority("node-1", "res1", 2000);
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

  it("onCreateRealm should do nothing when cannot submit", () => {
    component.newRealmName.set("");
    component.isCreatingRealm.set(false);

    component.onCreateRealm();

    expect(realmService.createRealm).not.toHaveBeenCalled();
  });

  it("onCreateRealm should create realm with global resolvers and optional priorities", () => {
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

    component.onCreateRealm();

    expect(realmService.createRealm).toHaveBeenCalledTimes(2);

    const callGlobal = (realmService.createRealm as jest.Mock).mock.calls[0];
    expect(callGlobal[0]).toBe("realmA");
    expect(callGlobal[1]).toBe("");
    expect(callGlobal[2]).toEqual([
      { name: "res1", priority: 10 },
      { name: "res2" }
    ]);

    const callNode = (realmService.createRealm as jest.Mock).mock.calls[1];
    expect(callNode[0]).toBe("realmA");
    expect(callNode[1]).toBe("node-1");
    expect(callNode[2]).toEqual([
      { name: "res3", priority: 5 },
      { name: "res4" }
    ]);

    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Realm created.");
    expect(component.newRealmName()).toBe("");
    expect(component.newRealmNodeResolvers()).toEqual({});
    expect(component.isCreatingRealm()).toBe(false);
    expect(realmService.realmResource.reload).toHaveBeenCalled();
  });

  it("onCreateRealm should create realm with empty resolver list when none configured", () => {
    component.newRealmName.set("realmEmpty");
    component.newRealmNodeResolvers.set({});

    component.onCreateRealm();

    expect(realmService.createRealm).toHaveBeenCalledTimes(1);
    const call = (realmService.createRealm as jest.Mock).mock.calls[0];
    expect(call[0]).toBe("realmEmpty");
    expect(call[1]).toBe("");
    expect(call[2]).toEqual([]);
  });

  it("startEditRealm should initialize editing state and maps", () => {
    const row = {
      name: "realmA",
      isDefault: false,
      resolversText: "",
      resolverGroups: [
        {
          nodeId: "",
          nodeLabel: "All nodes",
          resolvers: [
            { name: "res1", type: "ldap", priority: null }
          ]
        },
        {
          nodeId: "node-1",
          nodeLabel: "Node 1",
          resolvers: [
            { name: "res2", type: "sql", priority: 5 }
          ]
        }
      ]
    };

    component.startEditRealm(row as any);

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
    const row = { name: "realmA" } as any;

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
    const row = { name: "realmA" } as any;
    component.editingRealmName.set("realmA");
    component.editNodeResolvers.set({});

    component.saveEditedRealm(row);

    expect(notificationService.openSnackBar).toHaveBeenCalledWith("No resolvers configured.");
    expect(realmService.createRealm).not.toHaveBeenCalled();
    expect(component.isSavingEditedRealm()).toBe(false);
  });

  it("saveEditedRealm should send updated resolvers and reset editing state", () => {
    const row = { name: "realmA" } as any;

    component.editingRealmName.set("realmA");
    component.editNodeResolvers.set({
      "": [
        { name: "res1", priority: 10 },
        { name: "res2", priority: null }
      ],
      "node-1": [
        { name: "res3", priority: 7 }
      ]
    });

    component.saveEditedRealm(row);

    expect(realmService.createRealm).toHaveBeenCalledTimes(2);

    const callGlobal = (realmService.createRealm as jest.Mock).mock.calls[0];
    expect(callGlobal[0]).toBe("realmA");
    expect(callGlobal[1]).toBe("");
    expect(callGlobal[2]).toEqual([
      { name: "res1", priority: 10 },
      { name: "res2" }
    ]);

    const callNode = (realmService.createRealm as jest.Mock).mock.calls[1];
    expect(callNode[0]).toBe("realmA");
    expect(callNode[1]).toBe("node-1");
    expect(callNode[2]).toEqual([
      { name: "res3", priority: 7 }
    ]);

    expect(notificationService.openSnackBar).toHaveBeenCalledWith('Realm "realmA" updated.');
    expect(component.editingRealmName()).toBeNull();
    expect(component.isSavingEditedRealm()).toBe(false);
    expect(realmService.realmResource.reload).toHaveBeenCalled();
  });

  it("onDeleteRealm should do nothing when row has no name", () => {
    component.onDeleteRealm({} as any);
    expect(dialog.open).not.toHaveBeenCalled();
  });

  it("onDeleteRealm should delete realm when confirmed", () => {
    dialog.result$ = of(true);
    const row = { name: "realmA" } as any;

    component.onDeleteRealm(row);

    expect(dialog.open).toHaveBeenCalled();
    expect(realmService.deleteRealm).toHaveBeenCalledWith("realmA");
    expect(notificationService.openSnackBar).toHaveBeenCalledWith('Realm "realmA" deleted.');
    expect(realmService.realmResource.reload).toHaveBeenCalled();
  });

  it("onDeleteRealm should not delete when dialog is cancelled", () => {
    dialog.result$ = of(false);
    const row = { name: "realmA" } as any;

    component.onDeleteRealm(row);

    expect(dialog.open).toHaveBeenCalled();
    expect(realmService.deleteRealm).not.toHaveBeenCalled();
  });

  it("onSetDefaultRealm should do nothing when row has no name", () => {
    component.onSetDefaultRealm({} as any);
    expect(realmService.setDefaultRealm).not.toHaveBeenCalled();
  });

  it("onSetDefaultRealm should call service and reload resources", () => {
    const row = { name: "realmA" } as any;

    component.onSetDefaultRealm(row);

    expect(realmService.setDefaultRealm).toHaveBeenCalledWith("realmA");
    expect(notificationService.openSnackBar).toHaveBeenCalledWith('Realm "realmA" set as default.');
    expect(realmService.realmResource.reload).toHaveBeenCalled();
    expect(realmService.defaultRealmResource.reload).toHaveBeenCalled();
  });
});
