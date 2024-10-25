import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerTabComponent } from './container-tab.component';

describe('ContainerTabComponent', () => {
  let component: ContainerTabComponent;
  let fixture: ComponentFixture<ContainerTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTabComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainerTabComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
