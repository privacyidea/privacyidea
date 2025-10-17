import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerTableActionsComponent } from './container-table-actions.component';

describe('ContainerTableActionsComponent', () => {
  let component: ContainerTableActionsComponent;
  let fixture: ComponentFixture<ContainerTableActionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTableActionsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainerTableActionsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
