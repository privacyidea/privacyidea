import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { TokenDetailsMachineComponent } from "./token-details-machine.component";
import { MockContainerService, MockMachineService, MockOverflowService } from "../../../../../testing/mock-services";
import { MachineService } from "../../../../services/machine/machine.service";
import { ContentService } from "../../../../services/content/content.service";
import { OverflowService } from "../../../../services/overflow/overflow.service";

describe("TokenDetailsInfoComponent", () => {
  let component: TokenDetailsMachineComponent;
  let fixture: ComponentFixture<TokenDetailsMachineComponent>;

  let machineService: MockMachineService;
  let contentService: MockContainerService;
  let overflowService: MockOverflowService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsMachineComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineService, useClass: MockMachineService },
        { provide: ContentService, useValue: MockContainerService },
        { provide: OverflowService, useValue: MockOverflowService }
      ]
    }).compileComponents();

    machineService = TestBed.inject(MachineService) as unknown as MockMachineService;
    contentService = TestBed.inject(ContentService) as unknown as MockContainerService;
    overflowService = TestBed.inject(OverflowService) as unknown as MockOverflowService;

    fixture = TestBed.createComponent(TokenDetailsMachineComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
