import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { of } from "rxjs";

import { ContainerCreateComponent } from "./container-create.component";
import { MatDialog } from "@angular/material/dialog";
import { NotificationService } from "../../../services/notification/notification.service";
import { provideHttpClient } from "@angular/common/http";

const mockMatDialog = {
  open: () => ({ afterClosed: () => of(null) }),
  closeAll: () => {
  }
};

const mockNotificationService = {
  openSnackBar: () => {
  }
};

class MockIntersectionObserver {
  constructor(private callback: any, private options?: any) {}
  observe = jest.fn();
  disconnect = jest.fn();
}

Object.defineProperty(global, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver
});

describe("ContainerCreateComponent", () => {
  let component: ContainerCreateComponent;
  let fixture: ComponentFixture<ContainerCreateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerCreateComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        { provide: MatDialog, useValue: mockMatDialog },
        { provide: NotificationService, useValue: mockNotificationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
