import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerDetailsTokenTableComponent } from './container-details-token-table.component';

describe('ContainerDetailsTokenTableComponent', () => {
  let component: ContainerDetailsTokenTableComponent;
  let fixture: ComponentFixture<ContainerDetailsTokenTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsTokenTableComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsTokenTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
