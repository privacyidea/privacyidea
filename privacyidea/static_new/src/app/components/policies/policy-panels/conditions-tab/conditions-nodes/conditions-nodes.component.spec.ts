import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ConditionsNodesComponent } from "./conditions-nodes.component";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { PiNode, SystemService } from "../../../../../services/system/system.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatSelectChange } from "@angular/material/select";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";
import { MockSystemService } from "../../../../../../testing/mock-services/mock-system-service";
import "@angular/localize/init";

describe("ConditionsNodesComponent", () => {
  let component: ConditionsNodesComponent;
  let fixture: ComponentFixture<ConditionsNodesComponent>;
  let policyServiceMock: MockPolicyService;
  let systemServiceMock: MockSystemService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionsNodesComponent, NoopAnimationsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionsNodesComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    systemServiceMock = TestBed.inject(SystemService) as unknown as MockSystemService;
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should toggle all nodes", () => {
    systemServiceMock.nodes.set([
      { name: "node1", uuid: "1" },
      { name: "node2", uuid: "2" },
      { name: "node2", uuid: "3" }
    ]);
    fixture.detectChanges();
    component.toggleAllNodes();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ pinode: ["node1", "node2", "node2"] });

    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.emptyPolicy, pinode: ["node1", "node2", "node2"] });
    fixture.detectChanges();
    component.toggleAllNodes();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ pinode: [] });
  });

  it("should update selected pinodes", () => {
    const event = { value: ["node1"] } as MatSelectChange<string[]>;
    component.updateSelectedPinodes(event);
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ pinode: ["node1"] });
  });

  it("should add user agent", () => {
    component.addUserAgentFormControl.setValue("test-agent");
    component.addUserAgent();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ user_agents: ["test-agent"] });
  });

  it("should remove user agent", () => {
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.emptyPolicy, user_agents: ["test-agent"] });
    fixture.detectChanges();
    component.removeUserAgent("test-agent");
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ user_agents: [] });
  });

  it("should clear user agents", () => {
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.emptyPolicy, user_agents: ["test-agent"] });
    fixture.detectChanges();
    component.clearUserAgents();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ user_agents: [] });
  });

  it("should set valid time", () => {
    component.validTimeFormControl.setValue("Mon-Fri: 08-17");
    component.setValidTime();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ time: "Mon-Fri: 08-17" });
  });

  it("should set clients with ip addresses", () => {
    // Client as to be a ip address or hostname, so we test with valid strings
    component.clientFormControl.setValue("0.0.0.0/0, 192.168.1.1");
    component.setClients();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ client: ["0.0.0.0/0", "192.168.1.1"] });
  });

  it("should set clients with hostnames", () => {
    // Client as to be a ip address or hostname, so we test with valid strings
    component.clientFormControl.setValue("example.com, myserver.local");
    component.setClients();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ client: ["example.com", "myserver.local"] });
  });

  it("should set clients with both ip addresses and hostnames", () => {
    // Client as to be a ip address or hostname, so we test with valid strings
    component.clientFormControl.setValue("example.com, 192.168.1.1, myserver.local");
    component.setClients();
    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({
      client: ["example.com", "192.168.1.1", "myserver.local"]
    });
  });

  describe("validators", () => {
    describe("validTimeValidator", () => {
      it("should return null for valid time strings", () => {
        const validTimes = [
          "Mon-Fri: 08-17",
          "Sat: 0-23, Sun: 10-16",
          "Mon-Sun: 00-23",
          "Mon-Fri: 08-17, Sat-Sun: 10-16"
        ];
        validTimes.forEach((time) => {
          component.validTimeFormControl.setValue(time);
          expect(component.validTimeValidator(component.validTimeFormControl)).toBeNull();
        });
      });

      it("should return an error for invalid time strings", () => {
        const invalidTimes = ["invalid", "Mon-Fri", "Mon-Fri:08", "Mon-Fri:8-17", "Mon-Fri:08-17,"];
        invalidTimes.forEach((time) => {
          component.validTimeFormControl.setValue(time);
          expect(component.validTimeValidator(component.validTimeFormControl)).toEqual({
            invalidValidTime: { value: time }
          });
        });
      });
    });

    describe("clientValidator", () => {
      it("should return null for valid client strings", () => {
        const validClients = [
          "192.168.0.1",
          "192.168.0.0/24",
          "example.com",
          "192.168.0.1, example.com, 10.0.0.0/8",
          "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
          "2001:db8::/32"
        ];
        validClients.forEach((client) => {
          component.clientFormControl.setValue(client);
          expect(component.clientValidator(component.clientFormControl)).toBeNull();
        });
      });

      it("should return an error for invalid client strings", () => {
        const invalidClients = ["invalid", "192.168.0.256", "192.168.0.1/33"];
        invalidClients.forEach((client) => {
          component.clientFormControl.setValue(client);
          expect(component.clientValidator(component.clientFormControl)).toEqual({ invalidClient: { value: client } });
        });
      });
    });

    describe("userAgentValidator", () => {
      it("should return null for valid user agent strings", () => {
        const validUserAgents = ["Mozilla/5.0", "MyCustomAgent/1.0"];
        validUserAgents.forEach((ua) => {
          component.addUserAgentFormControl.setValue(ua);
          expect(component.userAgentValidator(component.addUserAgentFormControl)).toBeNull();
        });
      });

      it("should return an error for invalid user agent strings", () => {
        const invalidUserAgent = "invalid,";

        component.addUserAgentFormControl.setValue(invalidUserAgent);
        expect(component.userAgentValidator(component.addUserAgentFormControl)).toEqual({
          includesComma: { value: invalidUserAgent }
        });
      });
    });
  });
});
